import hashlib
import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path

import requests
import yt_dlp

from app.core.config import settings
from app.core.redis import get_redis
from app.services.video_service import detect_platform
from app.services.bilibili_service import extract_bvid, API_HEADERS

logger = logging.getLogger(__name__)

SUBTITLE_CACHE_TTL = 6 * 3600


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _parse_vtt(content: str) -> list[dict]:
    """Parse WebVTT content into subtitle items."""
    items = []
    blocks = re.split(r"\n\n+", content.strip())
    for block in blocks:
        lines = block.strip().split("\n")
        ts_line = None
        text_lines = []
        for line in lines:
            if "-->" in line:
                ts_line = line
            elif ts_line is not None:
                text_lines.append(line)
        if ts_line and text_lines:
            m = re.match(
                r"(\d+:?\d+:\d+[\.,]\d+)\s*-->\s*(\d+:?\d+[\.,]\d+)",
                ts_line,
            )
            if m:
                start = _ts_to_seconds(m.group(1))
                end = _ts_to_seconds(m.group(2))
                text = " ".join(text_lines)
                text = re.sub(r"<[^>]+>", "", text).strip()
                if text and (not items or items[-1]["text"] != text):
                    items.append({"start": start, "end": end, "text": text})
    return items


def _parse_srt(content: str) -> list[dict]:
    """Parse SRT content into subtitle items."""
    items = []
    blocks = re.split(r"\n\n+", content.strip())
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue
        ts_line = None
        text_lines = []
        for line in lines:
            if "-->" in line:
                ts_line = line
            elif ts_line is not None:
                text_lines.append(line)
        if ts_line and text_lines:
            m = re.match(
                r"(\d+:\d+:\d+[,\.]\d+)\s*-->\s*(\d+:\d+:\d+[,\.]\d+)",
                ts_line,
            )
            if m:
                start = _ts_to_seconds(m.group(1))
                end = _ts_to_seconds(m.group(2))
                text = " ".join(text_lines)
                text = re.sub(r"<[^>]+>", "", text).strip()
                if text:
                    items.append({"start": start, "end": end, "text": text})
    return items


def _ts_to_seconds(ts: str) -> float:
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return float(parts[0])


_LANG_PRIORITY = ["zh-Hans", "zh", "zh-CN", "en", "ja"]


def _build_subtitle_candidates(info: dict, fmt: str = "json3") -> list[tuple[str, str, str]]:
    """Build an ordered list of (url, lang, source_type) subtitle candidates.

    Order: manual subs by lang priority → auto subs in original language →
    auto translated subs by lang priority.  This avoids YouTube's aggressive
    rate-limiting on auto-translated subtitle requests.
    """
    subs = info.get("subtitles", {})
    auto_subs = info.get("automatic_captions", {})
    original_lang = info.get("language") or ""

    def _url_for(entries: list[dict]) -> str | None:
        target = next((e for e in entries if e.get("ext") == fmt), None)
        if not target and entries:
            target = entries[0]
        return target.get("url") if target else None

    candidates: list[tuple[str, str, str]] = []
    seen_urls: set[str] = set()

    def _add(url: str | None, lang: str, stype: str):
        if url and url not in seen_urls:
            seen_urls.add(url)
            candidates.append((url, lang, stype))

    # 1) Manual/human subtitles (never rate-limited)
    for lang in _LANG_PRIORITY:
        _add(_url_for(subs.get(lang, [])), lang, "manual")
    for lang in subs:
        if lang not in _LANG_PRIORITY:
            _add(_url_for(subs[lang]), lang, "manual")

    # 2) Auto subs in original language (not rate-limited)
    if original_lang and original_lang in auto_subs:
        _add(_url_for(auto_subs[original_lang]), original_lang, "auto")

    # 3) Auto translated subs (may be rate-limited)
    for lang in _LANG_PRIORITY:
        _add(_url_for(auto_subs.get(lang, [])), lang, "auto-translated")

    return candidates


def _parse_youtube_json3(data: dict) -> list[dict]:
    """Parse YouTube json3 subtitle format into our standard list."""
    raw = []
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text or text == "\n":
            continue
        start_ms = ev.get("tStartMs", 0)
        dur_ms = ev.get("dDurMs", 0)
        raw.append((start_ms, dur_ms, text))

    result = []
    for i, (start_ms, dur_ms, text) in enumerate(raw):
        start = round(start_ms / 1000, 2)
        if dur_ms > 0:
            end = round((start_ms + dur_ms) / 1000, 2)
        elif i + 1 < len(raw):
            end = round(raw[i + 1][0] / 1000, 2)
        else:
            end = round(start + 5, 2)
        result.append({"start": start, "end": end, "text": text})
    return result


def _fetch_subtitle_url(url: str, is_translated: bool = False) -> requests.Response | None:
    """Fetch a subtitle URL, with backoff retry only for translated subs."""
    max_retries = 3 if is_translated else 1
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 429:
                if attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.info(f"Rate limited (429), retrying in {wait}s")
                    time.sleep(wait)
                    continue
                return None
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError:
            return None
        except Exception as e:
            logger.warning(f"Subtitle URL fetch failed: {e}")
            return None
    return None


def _extract_ytdlp_subtitles(url: str) -> list[dict]:
    """Extract subtitles via yt-dlp with a multi-tier strategy:

    1. Primary: use json3 format URLs (lightweight, fast).
       Tries manual → original-lang auto → translated auto, stopping at
       the first successful download.  Manual and original-language auto
       subs are almost never rate-limited by YouTube; translated auto subs
       may 429, so they are tried last with retry.
    2. Fallback: let yt-dlp download VTT/SRT files to disk.
    """
    ydl_base_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    if settings.YOUTUBE_COOKIES_FILE:
        cookies_path = Path(settings.YOUTUBE_COOKIES_FILE)
        if cookies_path.is_file():
            ydl_base_opts["cookiefile"] = str(cookies_path)

    # --- Strategy 1: json3 candidates ---
    try:
        with yt_dlp.YoutubeDL(ydl_base_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        logger.warning(f"yt-dlp extract_info failed: {e}")
        return []

    if not info:
        return []

    for sub_url, lang, stype in _build_subtitle_candidates(info, fmt="json3"):
        resp = _fetch_subtitle_url(sub_url, is_translated=(stype == "auto-translated"))
        if not resp:
            continue
        try:
            result = _parse_youtube_json3(resp.json())
            if result:
                logger.info(f"YouTube subtitles OK via json3 ({lang}/{stype}, {len(result)} entries)")
                return result
        except Exception:
            continue

    # --- Strategy 2: yt-dlp file download (VTT/SRT) ---
    logger.info("json3 unavailable, falling back to yt-dlp file download")
    with tempfile.TemporaryDirectory() as tmpdir:
        sub_prefix = os.path.join(tmpdir, "sub")
        dl_opts = {
            **ydl_base_opts,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": _LANG_PRIORITY,
            "subtitlesformat": "vtt/srt/best",
            "outtmpl": sub_prefix,
            "retries": 5,
            "extractor_retries": 3,
            "socket_timeout": 30,
            "sleep_interval_subtitles": 1,
        }
        try:
            with yt_dlp.YoutubeDL(dl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            logger.warning(f"yt-dlp subtitle file download failed: {e}")
            return []

        sub_files = list(Path(tmpdir).glob("sub.*"))
        if not sub_files:
            return []

        chosen = None
        for lang_code in _LANG_PRIORITY:
            for f in sub_files:
                if f".{lang_code}." in f.name:
                    chosen = f
                    break
            if chosen:
                break
        if not chosen:
            chosen = sub_files[0]

        try:
            content = chosen.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read subtitle file {chosen}: {e}")
            return []

        if "WEBVTT" in content[:50]:
            return _parse_vtt(content)
        return _parse_srt(content)


def _get_bilibili_aid_cid(bvid: str, session: requests.Session) -> tuple[int | None, int | None]:
    """Get aid and cid for a Bilibili video."""
    try:
        resp = session.get(
            f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", timeout=15
        )
        vdata = resp.json().get("data", {})
        return vdata.get("aid"), vdata.get("cid")
    except Exception as e:
        logger.warning(f"Failed to get Bilibili aid/cid: {e}")
        return None, None


def _pick_subtitle_url(subtitle_list: list[dict]) -> str:
    """Pick the best subtitle track (prefer Chinese) and return its URL."""
    if not subtitle_list:
        return ""
    chosen = None
    for sub in subtitle_list:
        if sub.get("lan", "").startswith("zh"):
            chosen = sub
            break
    if not chosen:
        chosen = subtitle_list[0]
    sub_url = chosen.get("subtitle_url", "")
    if sub_url.startswith("http://"):
        sub_url = sub_url.replace("http://", "https://", 1)
    elif sub_url.startswith("//"):
        sub_url = "https:" + sub_url
    return sub_url


def _fetch_subtitle_body(sub_url: str, session: requests.Session) -> list[dict]:
    """Download subtitle JSON and convert to our item format."""
    if not sub_url:
        return []
    try:
        sub_resp = session.get(sub_url, timeout=15)
        body = sub_resp.json().get("body", [])
        return [
            {
                "start": entry.get("from", 0),
                "end": entry.get("to", 0),
                "text": entry.get("content", ""),
            }
            for entry in body
        ]
    except Exception as e:
        logger.warning(f"Failed to fetch subtitle body: {e}")
        return []


def _extract_bilibili_subtitles(url: str) -> list[dict]:
    """Extract CC subtitles from Bilibili.

    Strategy (no cookie needed):
      1. /x/v2/dm/view  – danmaku-view API returns subtitle URLs without login
      2. /x/player/v2   – player API (needs SESSDATA cookie to return subtitles)
    """
    bvid = extract_bvid(url)
    if not bvid:
        return []

    session = requests.Session()
    session.headers.update(API_HEADERS)

    aid, cid = _get_bilibili_aid_cid(bvid, session)
    if not cid:
        return []

    # Strategy 1: dm/view API (works without login)
    try:
        dm_resp = session.get(
            f"https://api.bilibili.com/x/v2/dm/view?aid={aid}&oid={cid}&type=1",
            timeout=15,
        )
        dm_data = dm_resp.json()
        if dm_data.get("code") == 0:
            subtitle_list = dm_data.get("data", {}).get("subtitle", {}).get("subtitles", [])
            sub_url = _pick_subtitle_url(subtitle_list)
            items = _fetch_subtitle_body(sub_url, session)
            if items:
                logger.info(f"Bilibili CC subtitles via dm/view: {len(items)} entries")
                return items
    except Exception as e:
        logger.warning(f"Bilibili dm/view subtitle attempt failed: {e}")

    # Strategy 2: player/v2 API (requires cookie)
    if settings.BILIBILI_COOKIE:
        session.headers["Cookie"] = settings.BILIBILI_COOKIE
    try:
        player_resp = session.get(
            f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}", timeout=15
        )
        subtitle_list = (
            player_resp.json().get("data", {}).get("subtitle", {}).get("subtitles", [])
        )
        sub_url = _pick_subtitle_url(subtitle_list)
        items = _fetch_subtitle_body(sub_url, session)
        if items:
            logger.info(f"Bilibili CC subtitles via player/v2: {len(items)} entries")
            return items
    except Exception as e:
        logger.warning(f"Bilibili player/v2 subtitle attempt failed: {e}")

    return []


def _extract_bilibili_danmaku(url: str) -> list[dict]:
    """Extract danmaku (弹幕) from Bilibili as a fallback context source."""
    import xml.etree.ElementTree as ET

    bvid = extract_bvid(url)
    if not bvid:
        return []

    session = requests.Session()
    session.headers.update(API_HEADERS)

    try:
        _, cid = _get_bilibili_aid_cid(bvid, session)
        if not cid:
            return []

        dm_resp = session.get(
            f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}", timeout=15
        )
        dm_resp.encoding = "utf-8"
        root = ET.fromstring(dm_resp.content)
        dms = root.findall(".//d")

        items = []
        for d in dms:
            if not d.text or not d.text.strip():
                continue
            attrs = d.attrib.get("p", "").split(",")
            ts = float(attrs[0]) if attrs else 0
            items.append({"start": ts, "end": ts + 2, "text": d.text.strip()})

        items.sort(key=lambda x: x["start"])
        return items

    except Exception as e:
        logger.warning(f"Bilibili danmaku extraction failed: {e}")
        return []


def _get_bilibili_metadata(url: str) -> dict:
    """Get Bilibili video metadata (title, description, tags)."""
    bvid = extract_bvid(url)
    if not bvid:
        return {}

    session = requests.Session()
    session.headers.update(API_HEADERS)

    try:
        info_resp = session.get(
            f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", timeout=15
        )
        vdata = info_resp.json().get("data", {})

        tags = []
        try:
            tags_resp = session.get(
                f"https://api.bilibili.com/x/tag/archive/tags?bvid={bvid}", timeout=10
            )
            tags_data = tags_resp.json().get("data", [])
            tags = [t.get("tag_name", "") for t in (tags_data or []) if t.get("tag_name")]
        except Exception:
            pass

        return {
            "title": vdata.get("title", ""),
            "description": vdata.get("desc", ""),
            "tags": tags,
            "duration": vdata.get("duration"),
            "owner": vdata.get("owner", {}).get("name", ""),
        }
    except Exception as e:
        logger.warning(f"Bilibili metadata extraction failed: {e}")
        return {}


def _get_ytdlp_metadata(url: str) -> dict:
    """Get video metadata via yt-dlp."""
    try:
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return {}
            return {
                "title": info.get("title", ""),
                "description": info.get("description", ""),
                "tags": info.get("tags", []) or [],
                "duration": info.get("duration"),
                "owner": info.get("uploader", ""),
            }
    except Exception as e:
        logger.warning(f"yt-dlp metadata extraction failed: {e}")
        return {}


async def extract_subtitles(url: str) -> dict:
    """Extract subtitles for a given video URL.

    Returns: {subtitles, full_text, source}
    """
    redis = get_redis()
    url_hash = _url_hash(url)
    cache_key = f"subtitle:{url_hash}"

    if redis:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

    platform = detect_platform(url)

    subtitles = []
    source = "none"
    if platform == "bilibili":
        subtitles = _extract_bilibili_subtitles(url)
        if subtitles:
            source = "cc"
        else:
            subtitles = _extract_bilibili_danmaku(url)
            if subtitles:
                source = "danmaku"
    elif platform == "douyin":
        subtitles = []
    else:
        subtitles = _extract_ytdlp_subtitles(url)
        if subtitles:
            source = "cc"

    full_text = " ".join(item["text"] for item in subtitles)

    result = {
        "subtitles": subtitles,
        "full_text": full_text,
        "source": source,
    }

    if redis:
        await redis.set(cache_key, json.dumps(result, ensure_ascii=False), ex=SUBTITLE_CACHE_TTL)

    return result


async def get_video_context(url: str) -> dict:
    """Get the best available text context for AI analysis.

    Priority: subtitles > danmaku > metadata.
    Returns: {source, text, metadata}
    """
    redis = get_redis()
    url_hash = _url_hash(url)
    cache_key = f"ai_context:{url_hash}"

    if redis:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

    sub_result = await extract_subtitles(url)
    if sub_result["full_text"].strip():
        result = {
            "source": "subtitle",
            "text": sub_result["full_text"],
        }
        if redis:
            await redis.set(cache_key, json.dumps(result, ensure_ascii=False), ex=SUBTITLE_CACHE_TTL)
        return result

    platform = detect_platform(url)

    if platform == "bilibili":
        danmaku = _extract_bilibili_danmaku(url)
        metadata = _get_bilibili_metadata(url)
    else:
        danmaku = []
        metadata = _get_ytdlp_metadata(url)

    parts = []

    if metadata.get("title"):
        parts.append(f"视频标题：{metadata['title']}")
    if metadata.get("owner"):
        parts.append(f"作者：{metadata['owner']}")
    if metadata.get("description"):
        parts.append(f"视频简介：{metadata['description']}")
    if metadata.get("tags"):
        parts.append(f"标签：{', '.join(metadata['tags'])}")

    if danmaku:
        unique_texts = []
        seen = set()
        for d in danmaku:
            t = d["text"]
            if t not in seen and len(t) > 2:
                seen.add(t)
                unique_texts.append(t)
        sampled = unique_texts[:500]
        parts.append(f"观众弹幕评论（{len(unique_texts)} 条）：\n" + "\n".join(sampled))

    text = "\n\n".join(parts)
    source = "danmaku" if danmaku else "metadata"

    result = {
        "source": source,
        "text": text,
    }

    if redis:
        await redis.set(cache_key, json.dumps(result, ensure_ascii=False), ex=SUBTITLE_CACHE_TTL)

    return result
