import json
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+aiomysql://omni:omni123@localhost:3306/omni_video"
    REDIS_URL: str = "redis://localhost:6379/0"
    DOWNLOAD_DIR: str = "./downloads"
    DOWNLOAD_CACHE_HOURS: int = 3
    CORS_ORIGINS: str = '["http://localhost:5173","http://localhost"]'

    @property
    def cors_origins_list(self) -> list[str]:
        return json.loads(self.CORS_ORIGINS)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

DOWNLOAD_PATH = Path(settings.DOWNLOAD_DIR)
DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
