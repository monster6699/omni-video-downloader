import json
import logging
import re
from urllib.parse import urlparse, parse_qs

import requests

logger = logging.getLogger(__name__)

MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"


def extract_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").removeprefix("www.").removeprefix("m.")

    if "douyin.com" not in host:
        return None

    path = parsed.path.rstrip("/")

    if "/video/" in path:
        return path.split("/video/")[-1]

    modal_id = parse_qs(parsed.query).get("modal_id")
    if modal_id:
        return modal_id[0]

    if "v.douyin.com" in host or path.startswith("/"):
        try:
            resp = requests.head(url, headers={"User-Agent": MOBILE_UA},
                                 allow_redirects=True, timeout=10)
            final = resp.url
            m = re.search(r"/video/(\d+)", final)
            if m:
                return m.group(1)
        except Exception:
            pass

    return None


def parse_douyin(url: str) -> dict:
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(f"无法识别抖音视频ID: {url}")

    share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"
    resp = requests.get(share_url, headers={"User-Agent": MOBILE_UA}, timeout=15)
    resp.raise_for_status()

    router_match = re.search(r'_ROUTER_DATA\s*=\s*(\{.+?\})\s*</script>', resp.text, re.DOTALL)
    if not router_match:
        raise ValueError("抖音页面结构变更，无法解析")

    data = json.loads(router_match.group(1))
    aweme = _find_video_detail(data)
    if not aweme:
        raise ValueError("未找到视频信息")

    video = aweme.get("video", {})
    play_addr = video.get("play_addr", {})
    play_urls = play_addr.get("url_list", [])
    cover_list = video.get("cover", {}).get("url_list", [])
    duration_ms = video.get("duration", 0)

    play_url = play_urls[0] if play_urls else ""
    no_wm_url = play_url.replace("/playwm/", "/play/")

    from urllib.parse import quote
    raw_cover = cover_list[0] if cover_list else ""
    thumbnail = f"/api/video/proxy/image?url={quote(raw_cover, safe='')}" if raw_cover else None

    return {
        "title": aweme.get("desc", "抖音视频"),
        "thumbnail": thumbnail,
        "duration": duration_ms // 1000 if duration_ms > 1000 else duration_ms,
        "platform": "douyin",
        "formats": [
            {
                "format_id": "no_watermark",
                "ext": "mp4",
                "resolution": f"{video.get('height', 0)}p" if video.get("height") else "720p",
                "filesize": None,
                "note": "无水印",
                "has_video": True,
                "has_audio": True,
            }
        ],
        "_download_url": no_wm_url,
    }


def download_douyin(url: str, save_path: str) -> str:
    info = parse_douyin(url)
    dl_url = info["_download_url"]
    if not dl_url:
        raise ValueError("无法获取抖音下载链接")

    resp = requests.get(dl_url, headers={"User-Agent": "Mozilla/5.0"}, stream=True, timeout=60)
    resp.raise_for_status()

    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return save_path


def _find_video_detail(obj, depth=0):
    if depth > 15:
        return None
    if isinstance(obj, dict):
        if "desc" in obj and "video" in obj and isinstance(obj.get("video"), dict):
            return obj
        if "awemeDetail" in obj:
            return obj["awemeDetail"]
        for v in obj.values():
            r = _find_video_detail(v, depth + 1)
            if r:
                return r
    elif isinstance(obj, list):
        for item in obj:
            r = _find_video_detail(item, depth + 1)
            if r:
                return r
    return None
