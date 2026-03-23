from datetime import datetime

from pydantic import BaseModel


class AdminUserItem(BaseModel):
    id: int
    phone: str | None = None
    nickname: str | None = None
    google_email: str | None = None
    is_vip: bool = False
    vip_expire_at: datetime | None = None
    ai_quota: int = 0
    is_admin: bool = False
    created_at: datetime
    download_count: int = 0
    ai_task_count: int = 0

    model_config = {"from_attributes": True}


class AdminUserList(BaseModel):
    items: list[AdminUserItem]
    total: int


class AdminUserUpdate(BaseModel):
    is_vip: bool | None = None
    vip_expire_at: datetime | None = None
    ai_quota: int | None = None
    is_admin: bool | None = None
    nickname: str | None = None


class AdminStats(BaseModel):
    total_users: int = 0
    vip_users: int = 0
    today_downloads: int = 0
    today_ai_tasks: int = 0
    ai_type_distribution: dict[str, int] = {}
