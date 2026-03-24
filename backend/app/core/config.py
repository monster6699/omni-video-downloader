import json
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+aiomysql://omni:omni123@localhost:3306/omni_video"
    REDIS_URL: str = "redis://localhost:6379/0"
    DOWNLOAD_DIR: str = "./downloads"
    DOWNLOAD_CACHE_HOURS: int = 3
    CORS_ORIGINS: str = '["http://localhost:5173","http://localhost"]'

    # Optional: for extracting Bilibili CC subtitles that require login.
    # Paste the full Cookie header value here (e.g. "SESSDATA=...; bili_jct=...; ...").
    BILIBILI_COOKIE: str = ""

    # Optional: path to a Netscape-format cookies.txt for YouTube.
    # Helps bypass 429 rate limits. Export via browser extension or yt-dlp.
    YOUTUBE_COOKIES_FILE: str = ""

    # Auth
    JWT_SECRET: str = "change-me-to-a-random-hex-string"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days
    GOOGLE_CLIENT_ID: str = ""

    # Task queue mode: "local" (asyncio.to_thread, 开发默认，无 RQ/多进程) 或 "queue"（生产 RQ worker）
    TASK_MODE: str = "local"

    OPENAI_API_BASE: str = "https://api.deepseek.com"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "deepseek-chat"

    # WeChat Pay
    WECHAT_MCH_ID: str = ""
    WECHAT_APP_ID: str = ""
    WECHAT_API_V3_KEY: str = ""
    WECHAT_PRIVATE_KEY: str = ""
    WECHAT_CERT_SERIAL: str = ""
    WECHAT_NOTIFY_URL: str = ""

    # Alipay
    ALIPAY_APP_ID: str = ""
    ALIPAY_PRIVATE_KEY: str = ""
    ALIPAY_PUBLIC_KEY: str = ""
    ALIPAY_NOTIFY_URL: str = ""

    # VIP pricing (unit: fen / 分)
    VIP_MONTHLY_PRICE: int = 990
    VIP_YEARLY_PRICE: int = 8800

    # Anonymous users: max LLM AI calls per calendar day (UTC), per client IP
    ANON_AI_DAILY_LIMIT: int = 5
    # Shown on /api/ai/usage-rules; new users get this from DB default (see User model)
    REGISTER_DEFAULT_AI_QUOTA: int = 5

    @property
    def cors_origins_list(self) -> list[str]:
        return json.loads(self.CORS_ORIGINS)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

DOWNLOAD_PATH = Path(settings.DOWNLOAD_DIR)
DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
