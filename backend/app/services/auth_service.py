"""Authentication business logic: register, login, Google OAuth, profile."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User

logger = logging.getLogger(__name__)


async def register_by_phone(
    db: AsyncSession, phone: str, password: str, nickname: str | None = None
) -> User:
    existing = await db.scalar(select(User).where(User.phone == phone))
    if existing:
        raise ValueError("该手机号已注册")

    user = User(
        phone=phone,
        password_hash=hash_password(password),
        nickname=nickname or f"用户{phone[-4:]}",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def login_by_phone(db: AsyncSession, phone: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.phone == phone))
    if not user or not user.password_hash:
        raise ValueError("手机号或密码错误")
    if not verify_password(password, user.password_hash):
        raise ValueError("手机号或密码错误")
    return user


async def login_or_register_google(
    db: AsyncSession, google_id: str, email: str, name: str | None, picture: str | None
) -> User:
    user = await db.scalar(select(User).where(User.google_id == google_id))
    if user:
        return user

    user_by_email = None
    if email:
        user_by_email = await db.scalar(select(User).where(User.google_email == email))

    if user_by_email:
        user_by_email.google_id = google_id
        if not user_by_email.avatar_url and picture:
            user_by_email.avatar_url = picture
        await db.commit()
        await db.refresh(user_by_email)
        return user_by_email

    user = User(
        google_id=google_id,
        google_email=email,
        nickname=name or email.split("@")[0] if email else "Google用户",
        avatar_url=picture,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.scalar(select(User).where(User.id == user_id))


def issue_token(user: User) -> str:
    return create_access_token({"sub": str(user.id)})
