"""
Download task queue: async task creation + threaded download with real-time progress.

Uses asyncio.to_thread to run blocking downloads in a thread pool so the event loop
stays responsive for polling requests. Progress updates use a sync Redis connection
inside the thread.
"""

import app.core.macos_fork_safety  # noqa: F401 — RQ worker 不经过 main.py，须在此尽早设置

import asyncio
import contextlib
import json
import logging
import os
import re
import threading
import time
import uuid
from pathlib import Path
from collections.abc import Iterator

import redis as sync_redis_mod
import yt_dlp

from app.core.config import DOWNLOAD_PATH, settings
from app.core.redis import get_redis
from app.services.bilibili_service import download_bilibili, parse_bilibili
from app.services.douyin_service import download_douyin, parse_douyin
from app.services.video_service import (
    DIRECT_LINK_PLATFORMS,
    _sanitize_filename,
    _url_hash,
    detect_platform,
)

logger = logging.getLogger(__name__)

# 与磁盘文件名 `{url_hash}_{quality}.mp4` 对齐；升级后可废弃旧 `dl:{hash}:*` 脏缓存
_DL_REDIS_CACHE_PREFIX = "dl:v2"

# 专用于 task:{id} 进度字段：进程内单例，多线程安全；勿在下载流程里 close（queue Worker 与主线程并发写进度）
_sync_progress_redis: sync_redis_mod.Redis | None = None
_sync_progress_lock = threading.Lock()


def _get_sync_redis_for_progress() -> sync_redis_mod.Redis:
    global _sync_progress_redis
    if _sync_progress_redis is None:
        with _sync_progress_lock:
            if _sync_progress_redis is None:
                _sync_progress_redis = sync_redis_mod.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                )
    return _sync_progress_redis


def _write_task_progress(
    task_id: str,
    progress: int | str | None = None,
    *,
    mapping: dict[str, str] | None = None,
) -> None:
    """更新 Redis 中任务进度。与「缓存用」连接分离，避免多线程 + close 导致 queue Worker 下进度卡在 10。"""
    try:
        cli = _get_sync_redis_for_progress()
        if mapping is not None:
            cli.hset(f"task:{task_id}", mapping=mapping)
        elif progress is not None:
            cli.hset(f"task:{task_id}", "progress", str(progress))
    except Exception as e:
        logger.warning("Redis task progress write failed task=%s: %s", task_id, e)


def _format_id_disk_suffix(format_id: str | None) -> str:
    """Safe single path segment for a format / quality id."""
    if not format_id:
        return "best"
    s = re.sub(r"[^a-zA-Z0-9._+-]", "_", str(format_id).strip())
    return (s[:48] if s else "best") or "best"


def _disk_name_for_quality(url_hash: str, format_id: str | None, ext: str = "mp4") -> str:
    """One on-disk file per (video URL, quality). Avoids identical /file/... URLs and browser caching wrong quality."""
    return f"{url_hash}_{_format_id_disk_suffix(format_id)}.{ext}"


async def create_download_task(
    url: str, format_id: str | None = None, user_id: int | None = None
) -> str:
    """Create a download task and start it in the background. Returns task_id."""
    task_id = uuid.uuid4().hex[:12]
    redis = get_redis()

    await redis.hset(
        f"task:{task_id}",
        mapping={
            "status": "pending",
            "progress": "0",
            "download_url": "",
            "filename": "",
            "method": "",
            "error": "",
            "url": url,
            "format_id": format_id if format_id is not None else "",
        },
    )
    await redis.expire(f"task:{task_id}", settings.DOWNLOAD_CACHE_HOURS * 3600 + 600)

    asyncio.create_task(_run_task(task_id, url, format_id, user_id))
    return task_id


async def query_task_status(task_id: str) -> dict | None:
    """Read task state from Redis."""
    redis = get_redis()
    if not redis:
        return None
    data = await redis.hgetall(f"task:{task_id}")
    if not data:
        return None
    return {
        "task_id": task_id,
        "status": data.get("status", "unknown"),
        "progress": int(data.get("progress", "0")),
        "download_url": data.get("download_url") or None,
        "filename": data.get("filename") or None,
        "method": data.get("method") or None,
        "error": data.get("error") or None,
    }


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


async def _run_task(
    task_id: str, url: str, format_id: str | None, user_id: int | None = None
):
    """Async wrapper: offload blocking download to thread pool,
    then persist the download record to MySQL."""
    redis = get_redis()
    try:
        result = await asyncio.to_thread(
            _blocking_download, task_id, url, format_id
        )
        await redis.hset(
            f"task:{task_id}",
            mapping={
                "status": "done",
                "progress": "100",
                "download_url": result["download_url"],
                "filename": result.get("filename", ""),
                "method": result.get("method", "server"),
            },
        )

        try:
            await _persist_download_history(url, format_id, user_id, result)
        except Exception:
            logger.warning("Failed to persist download history for %s", url, exc_info=True)

    except Exception as e:
        logger.exception("Task %s failed", task_id)
        try:
            await redis.hset(
                f"task:{task_id}",
                mapping={"status": "failed", "error": str(e)},
            )
        except Exception:
            pass


async def _persist_download_history(
    url: str, format_id: str | None, user_id: int | None, result: dict
):
    """Write download record to the unified download_history table."""
    from app.core.database import async_session
    from app.services.persist_service import get_video_by_url, record_download_history

    async with async_session() as db:
        video = await get_video_by_url(db, url)
        await record_download_history(
            db,
            url=url,
            user_id=user_id,
            video_id=video.id if video else None,
            platform=video.platform if video else detect_platform(url),
            title=video.title if video else None,
            thumbnail=video.thumbnail if video else None,
            format_id=format_id,
            method=result.get("method", "server"),
            status="done",
            file_path=result.get("download_url"),
        )


_MAX_RETRIES = 2
_RETRYABLE_ERRORS = (ConnectionError, TimeoutError, OSError)


@contextlib.contextmanager
def _approximate_progress_while_downloading(task_id: str) -> Iterator[None]:
    """B 站 / 抖音不用 yt-dlp，没有 progress_hooks；用后台线程缓慢推高进度，避免长期卡在 10。

    注意：旧逻辑 ``while not stop.wait(2)`` 在下载于 2 秒内结束时，wait 因 stop 立即返回 True，
    循环体一次都不执行，进度永远停在 10。改为先立刻推一次，再按「等 2s 或 stop」循环。
    """
    stop = threading.Event()
    current = [14]

    def pump() -> None:
        _write_task_progress(task_id, current[0])
        while True:
            if stop.wait(2.0):
                break
            current[0] = min(current[0] + 4, 90)
            _write_task_progress(task_id, current[0])

    th = threading.Thread(target=pump, daemon=True)
    th.start()
    try:
        yield
    finally:
        stop.set()
        th.join(timeout=2.0)


def _blocking_download(task_id: str, url: str, format_id: str | None) -> dict:
    """
    Synchronous download executed in a thread pool.
    Uses a dedicated sync Redis connection for progress updates and cache.
    Retries up to _MAX_RETRIES times on transient network errors.
    """
    r = sync_redis_mod.from_url(settings.REDIS_URL, decode_responses=True)

    try:
        _write_task_progress(
            task_id,
            mapping={"status": "downloading", "progress": "5"},
        )

        platform = detect_platform(url)
        url_hash = _url_hash(url)
        fmt_key = format_id or "best"
        cache_key = f"{_DL_REDIS_CACHE_PREFIX}:{url_hash}:{fmt_key}"

        cached = r.get(cache_key)
        if cached:
            data = json.loads(cached)
            if os.path.exists(data["file_path"]):
                return {
                    "download_url": f"/api/video/file/{data['disk_name']}",
                    "method": "server",
                    "filename": data["display_name"],
                }

        if platform in DIRECT_LINK_PLATFORMS:
            direct = _try_direct(url, format_id, platform)
            if direct:
                return direct

        _write_task_progress(task_id, 10)

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                result = _execute_download(task_id, url, format_id, platform, url_hash)
                break
            except _RETRYABLE_ERRORS as exc:
                last_error = exc
                if attempt < _MAX_RETRIES:
                    wait = 3 * (attempt + 1)
                    logger.warning(
                        "Task %s attempt %d failed (%s), retrying in %ds",
                        task_id, attempt + 1, exc, wait,
                    )
                    _write_task_progress(task_id, 10)
                    time.sleep(wait)
                else:
                    raise
        else:
            raise last_error  # type: ignore[misc]

        disk_name = result["disk_name"]
        display_name = result["display_name"]
        save_file = result["save_file"]

        cache_data = json.dumps(
            {
                "file_path": save_file,
                "disk_name": disk_name,
                "display_name": display_name,
            }
        )
        r.set(cache_key, cache_data, ex=settings.DOWNLOAD_CACHE_HOURS * 3600)

        return {
            "download_url": f"/api/video/file/{disk_name}",
            "method": "server",
            "filename": display_name,
        }
    finally:
        r.close()


def _execute_download(
    task_id: str,
    url: str,
    format_id: str | None,
    platform: str,
    url_hash: str,
) -> dict:
    """Core download logic, separated for retry wrapping."""
    if platform == "douyin":
        info = parse_douyin(url)
        disk_name = _disk_name_for_quality(url_hash, format_id)
        save_file = str(DOWNLOAD_PATH / disk_name)
        with _approximate_progress_while_downloading(task_id):
            download_douyin(url, save_file)
        display_name = f"{_sanitize_filename(info['title'])}.mp4"
    elif platform == "bilibili":
        info = parse_bilibili(url)
        disk_name = _disk_name_for_quality(url_hash, format_id)
        save_file = str(DOWNLOAD_PATH / disk_name)
        with _approximate_progress_while_downloading(task_id):
            download_bilibili(url, save_file, format_id)
        display_name = f"{_sanitize_filename(info['title'])}.mp4"
    else:
        fmt_seg = _format_id_disk_suffix(format_id)
        ydl_opts: dict = {
            "quiet": True,
            "no_warnings": True,
            "outtmpl": str(DOWNLOAD_PATH / f"{url_hash}_{fmt_seg}.%(ext)s"),
            "progress_hooks": [_make_progress_hook(task_id)],
        }
        if format_id:
            ydl_opts["format"] = format_id
        else:
            ydl_opts["format"] = "best"

        cookies_file = settings.YOUTUBE_COOKIES_FILE
        if cookies_file and platform == "youtube":
            ydl_opts["cookiefile"] = cookies_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if not info:
            raise ValueError("Download failed")

        save_file = ydl.prepare_filename(info)
        disk_name = Path(save_file).name
        title = info.get("title", "video")
        ext = info.get("ext", "mp4")
        display_name = f"{_sanitize_filename(title)}.{ext}"

    return {
        "disk_name": disk_name,
        "save_file": save_file,
        "display_name": display_name,
    }


def _try_direct(url: str, format_id: str | None, platform: str) -> dict | None:
    """Attempt to resolve a direct CDN download URL (sync)."""
    ydl_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": format_id or "best",
    }
    cookies_file = settings.YOUTUBE_COOKIES_FILE
    if cookies_file and platform == "youtube":
        ydl_opts["cookiefile"] = cookies_file
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info or info.get("requested_formats"):
            return None
        direct_url = info.get("url")
        if not direct_url:
            return None
        vcodec = info.get("vcodec", "none")
        acodec = info.get("acodec", "none")
        if vcodec == "none" or acodec == "none":
            return None
        title = info.get("title", "video")
        ext = info.get("ext", "mp4")
        return {
            "download_url": direct_url,
            "method": "direct",
            "filename": f"{_sanitize_filename(title)}.{ext}",
        }
    except Exception:
        return None


def _make_progress_hook(task_id: str):
    """yt-dlp progress hook → Redis ``progress`` (throttled ~1/s).

    Many流式格式没有 ``total_bytes`` / ``estimate``，原先 ``if total`` 不成立时进度永远停在 10。
    无总大小时按已运行时间缓慢推高到 88%（完成时由主流程写 100）。
    """
    last_written = [9]
    last_tick = [0.0]
    hook_started = time.time()

    def hook(d: dict):
        if d.get("status") != "downloading":
            return
        now = time.time()
        if now - last_tick[0] < 1.0:
            return

        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        downloaded = d.get("downloaded_bytes") or 0

        if total and total > 0:
            progress = min(int(downloaded * 90 / total) + 10, 99)
        else:
            elapsed = now - hook_started
            progress = min(10 + int(elapsed * 1.5), 88)

        if progress > last_written[0]:
            _write_task_progress(task_id, progress)
            last_written[0] = progress
            last_tick[0] = now

    return hook


# ---------------------------------------------------------------------------
# RQ entry-point (used by task_dispatcher in queue mode)
# ---------------------------------------------------------------------------

def _task_params_from_redis(
    r: sync_redis_mod.Redis, task_id: str, url: str, format_id: str | None
) -> tuple[str, str | None]:
    """RQ worker 与 API 进程分离，以 Redis 中 enqueue 时写入的字段为准，避免 job 参数序列化异常导致 format 丢失。"""
    meta = r.hgetall(f"task:{task_id}") or {}
    url_eff = (meta.get("url") or "").strip() or url
    raw_fmt = meta.get("format_id")
    if raw_fmt is None:
        format_eff = format_id
    elif raw_fmt == "":
        format_eff = None
    else:
        format_eff = str(raw_fmt).strip() or None
    return url_eff, format_eff


def blocking_download_job(
    task_id: str, url: str, format_id: str | None = None, user_id: int | None = None
) -> dict:
    """Top-level function for RQ workers. The task_id and initial Redis state
    are set up by the dispatcher before enqueuing."""
    try:
        cli = _get_sync_redis_for_progress()
        url_eff, format_eff = _task_params_from_redis(cli, task_id, url, format_id)
        result = _blocking_download(task_id, url_eff, format_eff)
        _write_task_progress(
            task_id,
            mapping={
                "status": "done",
                "progress": "100",
                "download_url": result["download_url"],
                "filename": result.get("filename", ""),
                "method": result.get("method", "server"),
            },
        )
        return {"task_id": task_id, **result}
    except Exception as e:
        logger.exception("RQ job %s failed", task_id)
        _write_task_progress(
            task_id,
            mapping={"status": "failed", "error": str(e)},
        )
        raise
