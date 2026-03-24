from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def _normalize_mysql_async_url(url: str) -> str:
    """aiomysql/pymysql 在高并发下易出现 Packet sequence wrong；统一走 asyncmy。"""
    if url.startswith("mysql+aiomysql://"):
        return "mysql+asyncmy://" + url.removeprefix("mysql+aiomysql://")
    return url


_db_url = _normalize_mysql_async_url(settings.DATABASE_URL)

# Driver: mysql+asyncmy. pool_recycle / pre_ping / reset help stale TCP.
engine = create_async_engine(
    _db_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=2800,
    pool_reset_on_return="rollback",
    pool_size=10,
    max_overflow=20,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
