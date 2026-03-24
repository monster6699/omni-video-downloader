import logging

import requests as http_requests
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_optional_user
from app.core.config import DOWNLOAD_PATH
from app.core.database import get_db
from app.core.task_dispatcher import dispatch_download
from app.models.user import User
from app.schemas.video import (
    DownloadTaskResponse,
    TaskStatusResponse,
    VideoDownloadRequest,
    VideoParseRequest,
    VideoParseResponse,
)
from app.services.persist_service import upsert_video
from app.services.task_service import query_task_status
from app.services.video_service import parse_video

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/parse", response_model=VideoParseResponse)
async def api_parse_video(
    req: VideoParseRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await parse_video(req.url)

        try:
            await upsert_video(
                db,
                url=req.url,
                platform=result.get("platform", "unknown"),
                title=result.get("title"),
                duration=result.get("duration"),
                thumbnail=result.get("thumbnail"),
            )
        except Exception:
            logger.warning("Failed to persist video record", exc_info=True)

        return VideoParseResponse(**result)
    except Exception as e:
        logger.exception("Parse failed")
        raise HTTPException(status_code=400, detail=f"解析失败: {str(e)}")


@router.post("/download", response_model=DownloadTaskResponse)
async def api_download_video(
    req: VideoDownloadRequest,
    user: User | None = Depends(get_optional_user),
):
    try:
        task_id = await dispatch_download(req.url, req.format_id, user.id if user else None)
        return DownloadTaskResponse(task_id=task_id, status="pending")
    except Exception as e:
        logger.exception("Failed to create download task")
        raise HTTPException(status_code=400, detail=f"创建下载任务失败: {str(e)}")


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def api_task_status(task_id: str):
    status = await query_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return TaskStatusResponse(**status)


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
        headers={
            # 同一视频多清晰度曾共用 URL，浏览器会缓存首次下载；禁止缓存视频本体
            "Cache-Control": "no-store",
        },
    )
