from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class SiteSettings(Base):
    """Singleton row id=1: runtime VIP list prices (fen). Env defaults used on first insert."""

    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vip_monthly_price_fen: Mapped[int] = mapped_column(Integer, nullable=False)
    vip_yearly_price_fen: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
