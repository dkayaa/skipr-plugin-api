from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Video(Base):
    __tablename__ = "videos"

    pk: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending")
    model_version: Mapped[str | None] = mapped_column(
        String(255), nullable=True)
    pipeline_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True)
    transcript_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True)
    intervals_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now())
