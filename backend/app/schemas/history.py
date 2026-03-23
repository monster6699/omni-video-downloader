from datetime import datetime

from pydantic import BaseModel


class RecordDownloadRequest(BaseModel):
    url: str
    platform: str
    title: str | None = None
    thumbnail: str | None = None
    format_id: str | None = None
    resolution: str | None = None
    method: str = "server"


class DownloadHistoryItem(BaseModel):
    id: int
    url: str
    platform: str
    title: str | None = None
    thumbnail: str | None = None
    format_id: str | None = None
    resolution: str | None = None
    method: str
    status: str = "done"
    file_path: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DownloadHistoryList(BaseModel):
    items: list[DownloadHistoryItem]
    total: int
