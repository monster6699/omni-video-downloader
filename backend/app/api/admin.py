"""Admin API: user management and usage statistics."""

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.ai_task import AITask
from app.models.download_history import DownloadHistory
from app.models.user import User
from app.schemas.admin import (
    AdminStats,
    AdminUserItem,
    AdminUserList,
    AdminUserUpdate,
    AdminVipPricing,
    AdminVipPricingUpdate,
)
from app.services.vip_pricing import get_site_settings, update_vip_prices_fen

logger = logging.getLogger(__name__)
router = APIRouter()


async def require_admin(user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user


@router.get("/users", response_model=AdminUserList)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", max_length=100),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    base = select(User)
    if keyword:
        pattern = f"%{keyword}%"
        base = base.where(
            or_(
                User.phone.ilike(pattern),
                User.nickname.ilike(pattern),
                User.google_email.ilike(pattern),
            )
        )

    total = await db.scalar(select(func.count()).select_from(base.subquery()))

    rows = (
        await db.scalars(
            base.order_by(desc(User.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items = []
    for u in rows:
        dl_count = await db.scalar(
            select(func.count()).select_from(DownloadHistory).where(DownloadHistory.user_id == u.id)
        ) or 0
        ai_count = await db.scalar(
            select(func.count()).select_from(AITask).where(AITask.user_id == u.id)
        ) or 0

        item = AdminUserItem(
            id=u.id,
            phone=u.phone,
            nickname=u.nickname,
            google_email=u.google_email,
            is_vip=u.is_vip,
            vip_expire_at=u.vip_expire_at,
            ai_quota=u.ai_quota,
            is_admin=u.is_admin,
            created_at=u.created_at,
            download_count=dl_count,
            ai_task_count=ai_count,
        )
        items.append(item)

    return AdminUserList(items=items, total=total or 0)


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    req: AdminUserUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    payload = req.model_dump(exclude_unset=True)
    if "is_vip" in payload:
        user.is_vip = req.is_vip
    if "vip_expire_at" in payload:
        user.vip_expire_at = req.vip_expire_at
    if "ai_quota" in payload:
        user.ai_quota = req.ai_quota
    if "is_admin" in payload:
        user.is_admin = req.is_admin
    if "nickname" in payload:
        user.nickname = req.nickname

    await db.commit()
    return {"ok": True}


@router.get("/stats", response_model=AdminStats)
async def get_stats(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    vip_users = await db.scalar(
        select(func.count()).select_from(User).where(User.is_vip == True)
    ) or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    today_downloads = await db.scalar(
        select(func.count()).select_from(DownloadHistory)
        .where(DownloadHistory.created_at >= today_start)
    ) or 0

    today_ai_tasks = await db.scalar(
        select(func.count()).select_from(AITask)
        .where(AITask.created_at >= today_start)
    ) or 0

    type_rows = (
        await db.execute(
            select(AITask.task_type, func.count())
            .where(AITask.created_at >= today_start)
            .group_by(AITask.task_type)
        )
    ).all()
    ai_type_distribution = {row[0]: row[1] for row in type_rows}

    return AdminStats(
        total_users=total_users,
        vip_users=vip_users,
        today_downloads=today_downloads,
        today_ai_tasks=today_ai_tasks,
        ai_type_distribution=ai_type_distribution,
    )


@router.get("/vip-pricing", response_model=AdminVipPricing)
async def get_vip_pricing(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await get_site_settings(db)
    return AdminVipPricing(
        monthly_fen=row.vip_monthly_price_fen,
        yearly_fen=row.vip_yearly_price_fen,
        updated_at=row.updated_at,
    )


@router.put("/vip-pricing", response_model=AdminVipPricing)
async def put_vip_pricing(
    req: AdminVipPricingUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await update_vip_prices_fen(db, req.monthly_fen, req.yearly_fen)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="价格无效：须为 1～99999999 分之间的整数",
        )
    return AdminVipPricing(
        monthly_fen=row.vip_monthly_price_fen,
        yearly_fen=row.vip_yearly_price_fen,
        updated_at=row.updated_at,
    )
