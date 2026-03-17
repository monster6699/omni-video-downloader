import hashlib
import json
import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

from app.core.config import DOWNLOAD_PATH, settings
from app.core.redis import get_redis
from app.services.bilibili_service import parse_bilibili, download_bilibili
from app.services.douyin_service import parse_douyin, download_douyin

logger = logging.getLogger(__name__)

PLATFORM_MAP = {
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "bilibili.com": "bilibili",
    "b23.tv": "bilibili",
    "douyin.com": "douyin",
    "tiktok.com": "tiktok",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "instagram.com": "instagram",
}


def detect_platform(url: str) -> str:
    hostname = urlparse(url).hostname or ""
    hostname = hostname.removeprefix("www.").removeprefix("m.")
    for domain, platform in PLATFORM_MAP.items():
        if hostname.endswith(domain):
            return platform
    return "unknown"


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|#\n\r\t]', "", name)
    name = name.replace(" ", "_")
    return name[:200].strip()


def _safe_disk_name(url_hash: str, ext: str = "mp4") -> str:
    return f"{url_hash}.{ext}"


async def parse_video(url: str) -> dict:
    redis = get_redis()
    cache_key = f"parse:{_url_hash(url)}"

    if redis:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

    platform = detect_platform(url)

    if platform == "douyin":
        result = parse_douyin(url)
        if redis:
            await redis.set(cache_key, json.dumps(result), ex=3600)
        return result

    if platform == "bilibili":
        result = parse_bilibili(url)
        if redis:
            await redis.set(cache_key, json.dumps(result), ex=3600)
        return result

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ValueError("Failed to parse video")

    formats = []
    seen_resolutions = set()
    for f in info.get("formats", []):
        height = f.get("height")
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        has_video = vcodec != "none"
        has_audio = acodec != "none"

        if not has_video:
            continue

        resolution = f"{height}p" if height else f.get("format_note", "unknown")
        if resolution in seen_resolutions:
            continue
        seen_resolutions.add(resolution)

        formats.append({
            "format_id": f.get("format_id", ""),
            "ext": f.get("ext", "mp4"),
            "resolution": resolution,
            "filesize": f.get("filesize") or f.get("filesize_approx"),
            "note": f.get("format_note", ""),
            "has_video": has_video,
            "has_audio": has_audio,
        })

    formats.sort(key=lambda x: _parse_height(x["resolution"]), reverse=True)

    result = {
        "title": info.get("title", "Unknown"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "platform": platform,
        "formats": formats,
    }

    if redis:
        await redis.set(cache_key, json.dumps(result), ex=3600)

    return result


def _parse_height(resolution: str) -> int:
    m = re.match(r"(\d+)", resolution)
    return int(m.group(1)) if m else 0


async def get_download_info(url: str, format_id: str | None = None) -> dict:
    return await _server_download(url, format_id)


async def _server_download(url: str, format_id: str | None) -> dict:
    redis = get_redis()
    url_hash = _url_hash(url)
    fmt_key = format_id or "best"
    cache_key = f"dl:{url_hash}:{fmt_key}"

    if redis:
        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            if os.path.exists(data["file_path"]):
                return {
                    "download_url": f"/api/video/file/{data['disk_name']}",
                    "method": "server",
                    "filename": data["display_name"],
                }

    platform = detect_platform(url)

    if platform == "douyin":
        info = parse_douyin(url)
        disk_name = _safe_disk_name(url_hash, "mp4")
        save_file = str(DOWNLOAD_PATH / disk_name)
        download_douyin(url, save_file)
        display_name = f"{_sanitize_filename(info['title'])}.mp4"
    elif platform == "bilibili":
        info = parse_bilibili(url)
        disk_name = _safe_disk_name(url_hash, "mp4")
        save_file = str(DOWNLOAD_PATH / disk_name)
        download_bilibili(url, save_file, format_id)
        display_name = f"{_sanitize_filename(info['title'])}.mp4"
    else:
        disk_name = _safe_disk_name(url_hash, "mp4")
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "outtmpl": str(DOWNLOAD_PATH / f"{url_hash}.%(ext)s"),
        }
        if format_id:
            ydl_opts["format"] = format_id
        else:
            ydl_opts["format"] = "best"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if not info:
            raise ValueError("Download failed")

        save_file = ydl.prepare_filename(info)
        disk_name = Path(save_file).name
        title = info.get("title", "video")
        ext = info.get("ext", "mp4")
        display_name = f"{_sanitize_filename(title)}.{ext}"

    if redis:
        cache_data = json.dumps({
            "file_path": save_file,
            "disk_name": disk_name,
            "display_name": display_name,
        })
        await redis.set(cache_key, cache_data, ex=settings.DOWNLOAD_CACHE_HOURS * 3600)

    return {
        "download_url": f"/api/video/file/{disk_name}",
        "method": "server",
        "filename": display_name,
    }
