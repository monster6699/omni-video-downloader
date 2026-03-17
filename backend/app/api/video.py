import logging
from pathlib import Path
from urllib.parse import unquote

import requests as http_requests
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from app.core.config import DOWNLOAD_PATH
from app.schemas.video import (
    VideoDownloadRequest,
    VideoDownloadResponse,
    VideoParseRequest,
    VideoParseResponse,
)
from app.services.video_service import get_download_info, parse_video

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/parse", response_model=VideoParseResponse)
async def api_parse_video(req: VideoParseRequest):
    try:
        result = await parse_video(req.url)
        return VideoParseResponse(**result)
    except Exception as e:
        logger.exception("Parse failed")
        raise HTTPException(status_code=400, detail=f"解析失败: {str(e)}")


@router.post("/download", response_model=VideoDownloadResponse)
async def api_download_video(req: VideoDownloadRequest):
    try:
        result = await get_download_info(req.url, req.format_id)
        return VideoDownloadResponse(**result)
    except Exception as e:
        logger.exception("Download failed")
        raise HTTPException(status_code=400, detail=f"下载失败: {str(e)}")


@router.get("/proxy/image")
async def proxy_image(url: str = Query(...)):
    try:
        resp = http_requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/",
        }, timeout=10)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "image/jpeg")
        return Response(content=resp.content, media_type=content_type,
                        headers={"Cache-Control": "public, max-age=86400"})
    except Exception:
        raise HTTPException(status_code=502, detail="图片加载失败")


@router.get("/file/{disk_name}")
async def serve_file(disk_name: str, name: str | None = None):
    file_path = DOWNLOAD_PATH / disk_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    safe_path = file_path.resolve()
    if not str(safe_path).startswith(str(DOWNLOAD_PATH.resolve())):
        raise HTTPException(status_code=403, detail="Forbidden")

    download_name = name or disk_name

    return FileResponse(
        path=str(safe_path),
        filename=download_name,
        media_type="application/octet-stream",
    )
