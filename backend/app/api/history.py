"""Download history API — requires authentication."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.download_history import DownloadHistory
from app.models.user import User
from app.schemas.history import (
    DownloadHistoryItem,
    DownloadHistoryList,
    RecordDownloadRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/downloads", response_model=DownloadHistoryItem)
async def record_download(
    req: RecordDownloadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = DownloadHistory(
        user_id=user.id,
        url=req.url,
        platform=req.platform,
        title=req.title,
        thumbnail=req.thumbnail,
        format_id=req.format_id,
        resolution=req.resolution,
        method=req.method,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return DownloadHistoryItem.model_validate(record)


@router.get("/downloads", response_model=DownloadHistoryList)
async def list_downloads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(
        select(func.count()).select_from(DownloadHistory).where(DownloadHistory.user_id == user.id)
    )
    rows = (
        await db.scalars(
            select(DownloadHistory)
            .where(DownloadHistory.user_id == user.id)
            .order_by(desc(DownloadHistory.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return DownloadHistoryList(
        items=[DownloadHistoryItem.model_validate(r) for r in rows],
        total=total or 0,
    )
