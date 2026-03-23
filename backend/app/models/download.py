from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Download(Base):
    __tablename__ = "downloads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    format_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(20), nullable=True)
    method: Mapped[str] = mapped_column(String(20), default="server")
    status: Mapped[str] = mapped_column(String(20), default="done")
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
