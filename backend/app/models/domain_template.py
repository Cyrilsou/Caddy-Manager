from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DomainTemplate(Base):
    """Reusable domain configuration template."""
    __tablename__ = "domain_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    force_https: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_websocket: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_cors: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_headers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    strip_prefix: Mapped[bool] = mapped_column(Boolean, default=False)
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    lb_policy: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
