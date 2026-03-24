import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import setup_logging
from app.core.redis import close_redis, init_redis
from app.api.video import router as video_router
from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.history import router as history_router
from app.api.admin import router as admin_router
from app.api.pay import router as pay_router

import app.models.user  # noqa: F401 — register ORM models
import app.models.video  # noqa: F401
import app.models.download_history  # noqa: F401
import app.models.ai_task  # noqa: F401
import app.models.order  # noqa: F401


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    yield
    await close_redis()


app = FastAPI(title="OmniVideo Downloader", version="0.1.0", lifespan=lifespan)


@app.exception_handler(DBAPIError)
async def dbapi_exception_handler(_request: Request, exc: DBAPIError):
    """Avoid plain-text 500; remote MySQL often drops connections on rollback (2013 / packet errors)."""
    logger.exception("Database driver error")
    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "数据库连接中断或超时，请稍后重试。若使用远程 MySQL，请检查网络、"
                "max_allowed_packet 与 wait_timeout。"
            )
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(video_router, prefix="/api/video", tags=["video"])
app.include_router(ai_router, prefix="/api/ai", tags=["ai"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(history_router, prefix="/api/user", tags=["user"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(pay_router, prefix="/api/pay", tags=["pay"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
