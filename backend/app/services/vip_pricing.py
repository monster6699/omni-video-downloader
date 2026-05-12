"""VIP plan metadata and prices loaded from DB (singleton site_settings), seeded from env."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.site_settings import SiteSettings

PLAN_META: dict[str, dict] = {
    "monthly": {
        "id": "monthly",
        "name": "月度 VIP",
        "duration_days": 30,
        "description": "每月自动续费，随时取消",
    },
    "yearly": {
        "id": "yearly",
        "name": "年度 VIP",
        "duration_days": 365,
        "description": "年付更划算，省下一大笔",
    },
}


def valid_plan_id(plan_id: str) -> bool:
    return plan_id in PLAN_META


async def get_site_settings(db: AsyncSession) -> SiteSettings:
    row = await db.get(SiteSettings, 1)
    if row is not None:
        return row
    row = SiteSettings(
        id=1,
        vip_monthly_price_fen=settings.VIP_MONTHLY_PRICE,
        vip_yearly_price_fen=settings.VIP_YEARLY_PRICE,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def plans_for_api(db: AsyncSession) -> list[dict]:
    s = await get_site_settings(db)
    out: list[dict] = []
    for pid in ("monthly", "yearly"):
        item = {**PLAN_META[pid], "price": s.vip_monthly_price_fen if pid == "monthly" else s.vip_yearly_price_fen}
        out.append(item)
    return out


async def price_fen_for_plan(db: AsyncSession, plan_id: str) -> int:
    if not valid_plan_id(plan_id):
        raise KeyError(plan_id)
    s = await get_site_settings(db)
    return s.vip_monthly_price_fen if plan_id == "monthly" else s.vip_yearly_price_fen


async def update_vip_prices_fen(
    db: AsyncSession, monthly_fen: int, yearly_fen: int
) -> SiteSettings:
    lo, hi = 1, 99_999_999
    if monthly_fen < lo or monthly_fen > hi or yearly_fen < lo or yearly_fen > hi:
        raise ValueError("price out of range")
    s = await get_site_settings(db)
    s.vip_monthly_price_fen = monthly_fen
    s.vip_yearly_price_fen = yearly_fen
    await db.commit()
    await db.refresh(s)
    return s
