from datetime import datetime

from pydantic import BaseModel, Field


# ---- Request ----

class RegisterRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=20)
    password: str = Field(..., min_length=6, max_length=128)
    nickname: str | None = None


class LoginRequest(BaseModel):
    phone: str
    password: str


class GoogleLoginRequest(BaseModel):
    id_token: str


# ---- Response ----

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    id: int
    phone: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    google_email: str | None = None
    is_vip: bool = False
    vip_expire_at: datetime | None = None
    vip_plan_id: str | None = None
    ai_quota: int = 5
    is_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile
