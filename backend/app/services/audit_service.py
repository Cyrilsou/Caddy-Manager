from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.security.middleware import get_client_ip

SENSITIVE_KEYS = {
    "password", "password_hash", "secret", "token", "api_token",
    "api_key", "secret_key", "cloudflare_api_token", "current_password",
    "new_password", "refresh_token", "access_token",
}


def _redact_sensitive(details: dict | None) -> dict | None:
    if not details or not isinstance(details, dict):
        return details
    redacted = {}
    for key, value in details.items():
        if key.lower() in SENSITIVE_KEYS:
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = _redact_sensitive(value)
        else:
            redacted[key] = value
    return redacted


async def log_audit(
    db: AsyncSession,
    user_id: int | None,
    action: str,
    resource_type: str | None = None,
    resource_id: int | None = None,
    details: dict | None = None,
    request: Request | None = None,
):
    ip = get_client_ip(request) if request else None
    ua = request.headers.get("user-agent", "")[:500] if request else None

    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=_redact_sensitive(details),
        ip_address=ip,
        user_agent=ua,
    )
    db.add(entry)
    await db.flush()
