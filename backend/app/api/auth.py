"""Auth API: register, login, Google OAuth, current-user profile."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.schemas.auth import (
    AuthResponse,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserProfile,
)
from app.services.auth_service import (
    get_user_by_id,
    issue_token,
    login_by_phone,
    login_or_register_google,
    register_by_phone,
)

logger = logging.getLogger(__name__)
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ------------------------------------------------------------------ deps
async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Mandatory auth: raises 401 if no valid token."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效或已过期")
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


async def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Optional auth: returns None for anonymous requests."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
        return await get_user_by_id(db, user_id)
    except Exception:
        logger.warning("get_optional_user: token present but invalid", exc_info=True)
        return None


# ------------------------------------------------------------------ endpoints

@router.post("/register", response_model=AuthResponse)
async def api_register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_by_phone(db, req.phone, req.password, req.nickname)
        token = issue_token(user)
        return AuthResponse(
            access_token=token,
            user=UserProfile.model_validate(user),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Register failed")
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")


@router.post("/login", response_model=AuthResponse)
async def api_login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await login_by_phone(db, req.phone, req.password)
        token = issue_token(user)
        return AuthResponse(
            access_token=token,
            user=UserProfile.model_validate(user),
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.exception("Login failed")
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.post("/google", response_model=AuthResponse)
async def api_google_login(req: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        idinfo = google_id_token.verify_oauth2_token(
            req.id_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )

        google_id = idinfo["sub"]
        email = idinfo.get("email", "")
        name = idinfo.get("name")
        picture = idinfo.get("picture")

        user = await login_or_register_google(db, google_id, email, name, picture)
        token = issue_token(user)
        return AuthResponse(
            access_token=token,
            user=UserProfile.model_validate(user),
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Google 验证失败: {str(e)}")
    except Exception as e:
        logger.exception("Google login failed")
        raise HTTPException(status_code=500, detail=f"Google 登录失败: {str(e)}")


@router.get("/me", response_model=UserProfile)
async def api_get_profile(user=Depends(get_current_user)):
    return UserProfile.model_validate(user)
