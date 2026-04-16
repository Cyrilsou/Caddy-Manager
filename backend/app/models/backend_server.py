from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BackendServer(Base):
    __tablename__ = "backends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[str] = mapped_column(String(10), default="http", nullable=False)
    health_check_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    health_check_path: Mapped[str] = mapped_column(String(255), default="/")
    health_check_interval_sec: Mapped[int] = mapped_column(Integer, default=30)
    health_status: Mapped[str] = mapped_column(String(20), default="unknown")
    health_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    health_response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tls_skip_verify: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    domains = relationship("Domain", back_populates="backend", lazy="selectin")
