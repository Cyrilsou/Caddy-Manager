from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    backend_id: Mapped[int] = mapped_column(Integer, ForeignKey("backends.id"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    path_prefix: Mapped[str] = mapped_column(String(255), default="/")
    strip_prefix: Mapped[bool] = mapped_column(Boolean, default=False)
    force_https: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_websocket: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_cors: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_headers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    basic_auth: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_allowlist: Mapped[str | None] = mapped_column(Text, nullable=True)
    redirect_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    redirect_code: Mapped[int] = mapped_column(Integer, default=0)  # 0 = no redirect, 301, 302
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    zone_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dns_record_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    proxied: Mapped[bool] = mapped_column(Boolean, default=True)
    ssl_mode: Mapped[str] = mapped_column(String(20), default="full")
    lb_policy: Mapped[str] = mapped_column(String(20), default="")  # "", "round_robin", "least_conn", "first", "ip_hash"
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    backend = relationship("BackendServer", back_populates="domains", lazy="selectin")
    certificate = relationship("Certificate", back_populates="domain", uselist=False, lazy="selectin")
