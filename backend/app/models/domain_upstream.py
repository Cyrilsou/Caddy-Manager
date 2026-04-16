from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DomainUpstream(Base):
    """Many-to-many: a domain can have multiple backend upstreams for load balancing."""
    __tablename__ = "domain_upstreams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    domain_id: Mapped[int] = mapped_column(Integer, ForeignKey("domains.id", ondelete="CASCADE"), index=True)
    backend_id: Mapped[int] = mapped_column(Integer, ForeignKey("backends.id", ondelete="CASCADE"), index=True)
    weight: Mapped[int] = mapped_column(Integer, default=1)
