from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    yield
    await close_redis()


app = FastAPI(title="OmniVideo Downloader", version="0.1.0", lifespan=lifespan)

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
