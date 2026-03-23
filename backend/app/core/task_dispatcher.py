"""
Dual-mode task dispatcher: abstracts download scheduling so switching between
local (asyncio.to_thread) and queue (RQ) requires only an env-var change.

TASK_MODE=local  -> current asyncio.to_thread (default, for dev)
TASK_MODE=queue  -> Redis Queue + independent worker (for production)
"""

import logging
import uuid

import redis as sync_redis_mod

from app.core.config import settings

logger = logging.getLogger(__name__)


async def dispatch_download(
    url: str,
    format_id: str | None = None,
    user_id: int | None = None,
) -> str:
    """Create a download task and return a task_id. Routes to the
    appropriate backend based on ``settings.TASK_MODE``."""

    mode = settings.TASK_MODE

    if mode == "local":
        from app.services.task_service import create_download_task

        return await create_download_task(url, format_id, user_id)

    if mode == "queue":
        return _enqueue_rq(url, format_id, user_id)

    raise ValueError(f"Unknown TASK_MODE: {mode}")


def _enqueue_rq(url: str, format_id: str | None, user_id: int | None) -> str:
    """Enqueue a download job via RQ. The task_id is created upfront so
    the API can return it immediately for polling."""
    try:
        from rq import Queue
    except ImportError:
        raise RuntimeError("RQ is not installed. Install with: pip install rq")

    from app.services.task_service import blocking_download_job

    task_id = uuid.uuid4().hex[:12]

    r = sync_redis_mod.from_url(settings.REDIS_URL, decode_responses=True)
    r.hset(
        f"task:{task_id}",
        mapping={
            "status": "pending",
            "progress": "0",
            "download_url": "",
            "filename": "",
            "method": "",
            "error": "",
            "user_id": str(user_id) if user_id else "",
        },
    )
    r.expire(f"task:{task_id}", settings.DOWNLOAD_CACHE_HOURS * 3600 + 600)
    r.close()

    redis_conn = sync_redis_mod.from_url(settings.REDIS_URL)
    q = Queue("video_tasks", connection=redis_conn)
    q.enqueue(
        blocking_download_job,
        task_id,
        url,
        format_id,
        user_id,
        job_timeout="30m",
    )

    return task_id
