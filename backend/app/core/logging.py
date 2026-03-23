import logging
import os
from logging.config import dictConfig
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


class SizeAndTimeRotatingFileHandler(TimedRotatingFileHandler):
    """
    Rotate at a fixed time interval (e.g. daily at midnight) OR when the file
    exceeds maxBytes.

    This matches "按天/大小轮转" without extra dependencies.
    """

    def __init__(
        self,
        filename: str,
        when: str = "midnight",
        interval: int = 1,
        backupCount: int = 14,
        encoding: str | None = "utf-8",
        delay: bool = True,
        utc: bool = False,
        atTime=None,
        maxBytes: int = 100 * 1024 * 1024,  # 100MB
    ):
        self.maxBytes = int(maxBytes) if maxBytes else 0
        super().__init__(
            filename=filename,
            when=when,
            interval=interval,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            utc=utc,
            atTime=atTime,
        )

    def shouldRollover(self, record: logging.LogRecord) -> int:  # noqa: N802
        # Time-based rollover check from TimedRotatingFileHandler.
        if super().shouldRollover(record):
            return 1

        # Size-based rollover check.
        if self.maxBytes <= 0:
            return 0

        try:
            if self.stream is None:  # delay=True and not opened yet
                self.stream = self._open()
            self.stream.flush()

            try:
                current_size = os.stat(self.baseFilename).st_size
            except FileNotFoundError:
                current_size = 0

            msg = f"{self.format(record)}\n"
            if current_size + len(msg.encode(self.encoding or "utf-8")) >= self.maxBytes:
                return 1
        except Exception:
            # Never break app execution due to logging rollover edge-cases.
            return 0

        return 0


def _default_log_file() -> Path:
    # backend/app/core/logging.py -> parents[2] == backend/
    backend_dir = Path(__file__).resolve().parents[2]
    return backend_dir / "logs" / "app.log"


def setup_logging(
    *,
    log_file: str | Path | None = None,
    level: str = "INFO",
    max_bytes: int = 100 * 1024 * 1024,
    backup_count: int = 14,
) -> Path:
    log_path = Path(log_file) if log_file else _default_log_file()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": fmt, "datefmt": datefmt},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": level,
                },
                "file": {
                    "()": SizeAndTimeRotatingFileHandler,
                    "filename": str(log_path),
                    "when": "midnight",
                    "interval": 1,
                    "backupCount": backup_count,
                    "encoding": "utf-8",
                    "delay": True,
                    "utc": False,
                    "maxBytes": max_bytes,
                    "formatter": "default",
                    "level": level,
                },
            },
            "root": {"level": level, "handlers": ["console", "file"]},
            # Ensure uvicorn logs also go to our handlers.
            "loggers": {
                "uvicorn": {"level": level, "propagate": True},
                "uvicorn.error": {"level": level, "propagate": True},
                "uvicorn.access": {"level": level, "propagate": True},
            },
        }
    )

    return log_path

