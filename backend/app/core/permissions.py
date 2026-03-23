"""Permission dependencies: VIP checks, AI quota, etc."""

from datetime import datetime, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.datetime_utils import to_utc_aware, utc_now
from app.core.redis import get_redis
from app.models.user import User


def user_has_active_vip(user: User) -> bool:
    """True if VIP flag is on and not past expiry."""
    if not user.is_vip:
        return False
    if user.vip_expire_at and to_utc_aware(user.vip_expire_at) < utc_now():
        return False
    return True


def anon_ai_redis_key(request: Request) -> tuple[str, str, str]:
    """Return (redis_key, utc_date_str, client_ip)."""
    ip = get_client_ip(request)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (f"anon:ai:{day}:{ip}", day, ip)


async def read_anon_ai_used_today(request: Request) -> tuple[int | None, bool]:
    """How many LLM AI calls this IP has consumed today (Redis INCR value).
    Returns (used_count, redis_available). used_count is None if Redis unavailable."""
    r = get_redis()
    if not r:
        return None, False
    key, _, _ = anon_ai_redis_key(request)
    raw = await r.get(key)
    used = int(raw) if raw is not None else 0
    return used, True


def get_client_ip(request: Request) -> str:
    """Client IP for rate limiting (first hop in X-Forwarded-For when behind proxy)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return (request.client.host or "unknown")[:64]
    return "unknown"


async def check_anon_ai_quota(request: Request) -> None:
    """Limit anonymous LLM AI usage per IP per UTC day (Redis)."""
    r = get_redis()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务暂不可用，请稍后再试或登录后使用",
        )

    key, _, _ = anon_ai_redis_key(request)

    n = await r.incr(key)
    if n == 1:
        await r.expire(key, 90000)

    if n > settings.ANON_AI_DAILY_LIMIT:
        await r.decr(key)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"未登录用户每日可使用 AI 分析 {settings.ANON_AI_DAILY_LIMIT} 次（今日已用尽）。"
                "登录可获得更多免费次数，开通 VIP 可无限使用。"
            ),
        )


async def require_vip(user: User, db: AsyncSession) -> User:
    """Raise 403 if the user is not an active VIP."""
    if not user.is_vip:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="此功能需要 VIP 会员")
    if user.vip_expire_at and to_utc_aware(user.vip_expire_at) < utc_now():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="VIP 已过期，请续费")
    return user


async def check_ai_llm_access(
    user: User | None,
    db: AsyncSession,
    request: Request,
) -> None:
    """Logged-in: VIP / ai_quota. Anonymous: daily IP limit in Redis."""
    if user:
        await check_ai_quota(user, db)
    else:
        await check_anon_ai_quota(request)


async def check_ai_quota(user: User, db: AsyncSession) -> User:
    """Check and decrement free AI quota. VIP users are unlimited.
    Raises 403 if free quota is exhausted."""
    if user.is_vip:
        if user.vip_expire_at and to_utc_aware(user.vip_expire_at) < utc_now():
            pass  # VIP expired — fall through to quota check
        else:
            return user

    if user.ai_quota <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="今日免费 AI 次数已用完，升级 VIP 无限使用",
        )

    user.ai_quota -= 1
    await db.commit()
    return user
