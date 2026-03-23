from pydantic import BaseModel


class VideoFormat(BaseModel):
    format_id: str
    ext: str
    resolution: str | None = None
    filesize: int | None = None
    note: str | None = None
    has_video: bool = True
    has_audio: bool = True


class VideoParseRequest(BaseModel):
    url: str


class VideoParseResponse(BaseModel):
    title: str
    thumbnail: str | None = None
    duration: int | None = None
    platform: str
    formats: list[VideoFormat] = []


class VideoDownloadRequest(BaseModel):
    url: str
    format_id: str | None = None


class VideoDownloadResponse(BaseModel):
    download_url: str
    method: str  # "direct" or "server"
    filename: str | None = None


class DownloadTaskResponse(BaseModel):
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # pending | downloading | done | failed
    progress: int = 0
    download_url: str | None = None
    filename: str | None = None
    method: str | None = None
    error: str | None = None
