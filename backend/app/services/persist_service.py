"""
Persistence helpers: write video metadata, download history, and AI tasks to MySQL.

All functions accept an AsyncSession and handle their own commit so callers
only need to pass the session from the FastAPI dependency.
"""

import asyncio
import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session

from app.models.ai_task import AITask
from app.models.download_history import DownloadHistory
from app.models.video import Video

logger = logging.getLogger(__name__)


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


async def upsert_video(
    db: AsyncSession,
    url: str,
    platform: str,
    title: str | None = None,
    duration: int | None = None,
    thumbnail: str | None = None,
) -> Video:
    """Insert a video record or return the existing one (dedup by url_hash)."""
    url_hash = _url_hash(url)
    stmt = select(Video).where(Video.url_hash == url_hash)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()

    if video:
        if title and not video.title:
            video.title = title
        if duration and not video.duration:
            video.duration = duration
        if thumbnail and not video.thumbnail:
            video.thumbnail = thumbnail
        await db.commit()
        return video

    video = Video(
        url=url,
        url_hash=url_hash,
        platform=platform,
        title=title,
        duration=duration,
        thumbnail=thumbnail,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video


async def get_video_by_url(db: AsyncSession, url: str) -> Video | None:
    url_hash = _url_hash(url)
    stmt = select(Video).where(Video.url_hash == url_hash)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def record_download_history(
    db: AsyncSession,
    url: str,
    user_id: int | None = None,
    video_id: int | None = None,
    platform: str = "unknown",
    title: str | None = None,
    thumbnail: str | None = None,
    format_id: str | None = None,
    resolution: str | None = None,
    method: str = "server",
    status: str = "done",
    file_path: str | None = None,
) -> DownloadHistory:
    """Write a unified download history record."""
    record = DownloadHistory(
        user_id=user_id,
        video_id=video_id,
        url=url,
        platform=platform,
        title=title,
        thumbnail=thumbnail,
        format_id=format_id,
        resolution=resolution,
        method=method,
        status=status,
        file_path=file_path,
    )
    db.add(record)
    await db.commit()
    return record


async def record_ai_task(
    db: AsyncSession,
    task_type: str,
    user_id: int | None = None,
    video_id: int | None = None,
    status: str = "done",
    result_snapshot: str | None = None,
) -> AITask:
    """Write an AI task record for billing and analytics."""
    task = AITask(
        user_id=user_id,
        video_id=video_id,
        task_type=task_type,
        status=status,
        result_snapshot=result_snapshot,
    )
    db.add(task)
    await db.commit()
    return task


async def persist_ai_task_for_url(
    *,
    url: str,
    task_type: str,
    user_id: int | None = None,
    result_snapshot: str | None = None,
    max_attempts: int = 4,
) -> None:
    """Open a fresh session per attempt; retries on transient MySQL/driver errors
    (e.g. asyncmy packet sequence / handshake flakiness on remote DB)."""
    delay = 0.35
    for attempt in range(max_attempts):
        try:
            async with async_session() as db:
                video = await get_video_by_url(db, url)
                await record_ai_task(
                    db,
                    task_type=task_type,
                    user_id=user_id,
                    video_id=video.id if video else None,
                    status="done",
                    result_snapshot=result_snapshot,
                )
            return
        except DBAPIError as e:
            if attempt < max_attempts - 1:
                logger.info(
                    "persist_ai_task %s DBAPIError (attempt %s/%s), retry in %.2fs: %s",
                    task_type,
                    attempt + 1,
                    max_attempts,
                    delay,
                    e,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 3.0)
            else:
                logger.warning(
                    "Failed to persist AI task %s after %s attempts",
                    task_type,
                    max_attempts,
                    exc_info=True,
                )
                return
        except Exception:
            logger.warning("Failed to persist AI task %s", task_type, exc_info=True)
            return
