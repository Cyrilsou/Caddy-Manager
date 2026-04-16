import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import delete

from app.database import async_session_factory
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

RETENTION_DAYS = 90


async def cleanup_old_audit_logs():
    """Delete audit logs older than RETENTION_DAYS."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        async with async_session_factory() as session:
            result = await session.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff)
            )
            await session.commit()
            deleted = result.rowcount
            if deleted > 0:
                logger.info("Cleaned up %d audit log entries older than %d days", deleted, RETENTION_DAYS)
    except Exception:
        logger.exception("Audit log cleanup failed")
