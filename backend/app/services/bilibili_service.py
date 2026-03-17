import logging
import re
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}

QN_MAP = {
    127: "8K",
    126: "杜比视界",
    125: "HDR",
    120: "4K",
    116: "1080P60",
    112: "1080P+",
    80: "1080P",
    64: "720P",
    32: "480P",
    16: "360P",
}


def extract_bvid(url: str) -> str | None:
    m = re.search(r"(BV[\w]+)", url)
    return m.group(1) if m else None


def parse_bilibili(url: str) -> dict:
    bvid = extract_bvid(url)
    if not bvid:
        raise ValueError(f"无法识别B站视频ID: {url}")

    session = requests.Session()
    session.headers.update(API_HEADERS)

    info_resp = session.get(
        f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", timeout=15
    )
    info_data = info_resp.json()
    if info_data.get("code") != 0:
        raise ValueError(f"B站API错误: {info_data.get('message', 'unknown')}")

    vdata = info_data["data"]
    cid = vdata["cid"]

    stream_resp = session.get(
        f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=127&fnval=0&fourk=1",
        timeout=15,
    )
    stream_data = stream_resp.json()
    accept_quality = stream_data.get("data", {}).get("accept_quality", [])
    accept_desc = stream_data.get("data", {}).get("accept_description", [])

    formats = []
    for qn, desc in zip(accept_quality, accept_desc):
        filesize = None
        try:
            qn_resp = session.get(
                f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn={qn}&fnval=0",
                timeout=10,
            )
            durl = qn_resp.json().get("data", {}).get("durl", [])
            if durl:
                filesize = durl[0].get("size")
        except Exception:
            pass

        formats.append({
            "format_id": str(qn),
            "ext": "mp4",
            "resolution": desc,
            "filesize": filesize,
            "note": desc,
            "has_video": True,
            "has_audio": True,
        })

    raw_thumbnail = vdata.get("pic", "")
    if raw_thumbnail and raw_thumbnail.startswith("http://"):
        raw_thumbnail = raw_thumbnail.replace("http://", "https://", 1)

    from urllib.parse import quote
    thumbnail = f"/api/video/proxy/image?url={quote(raw_thumbnail, safe='')}" if raw_thumbnail else None

    return {
        "title": vdata.get("title", "B站视频"),
        "thumbnail": thumbnail,
        "duration": vdata.get("duration"),
        "platform": "bilibili",
        "formats": formats,
        "_bvid": bvid,
        "_cid": cid,
    }


def download_bilibili(url: str, save_path: str, format_id: str | None = None) -> str:
    bvid = extract_bvid(url)
    if not bvid:
        raise ValueError(f"无法识别B站视频ID: {url}")

    session = requests.Session()
    session.headers.update(API_HEADERS)

    info_resp = session.get(
        f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", timeout=15
    )
    cid = info_resp.json()["data"]["cid"]

    qn = int(format_id) if format_id else 80

    stream_resp = session.get(
        f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn={qn}&fnval=0&fourk=1",
        timeout=15,
    )
    sdata = stream_resp.json().get("data", {})
    durl = sdata.get("durl", [])
    if not durl:
        raise ValueError("无法获取B站下载链接")

    video_url = durl[0]["url"]

    resp = session.get(video_url, stream=True, timeout=120)
    resp.raise_for_status()

    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return save_path
