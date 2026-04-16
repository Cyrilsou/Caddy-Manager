import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.setting import Setting

logger = logging.getLogger(__name__)

ALERT_LEVELS = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴"}


async def _get_setting(key: str) -> str | None:
    async with async_session_factory() as session:
        result = await session.execute(select(Setting).where(Setting.key == key))
        s = result.scalar_one_or_none()
        return s.value if s else None


async def send_alert(title: str, message: str, level: str = "warning"):
    """Dispatch alert to all configured channels."""
    icon = ALERT_LEVELS.get(level, "ℹ️")
    full_title = f"{icon} Caddy Panel — {title}"

    webhook_url = await _get_setting("alert_webhook_url")
    if webhook_url:
        await _send_webhook(webhook_url, full_title, message)

    smtp_host = await _get_setting("smtp_host")
    if smtp_host:
        await _send_email(full_title, message)


async def _send_webhook(url: str, title: str, message: str):
    """Send to Discord or Slack webhook."""
    try:
        is_discord = "discord" in url.lower()

        if is_discord:
            payload = {
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": 0xFF4444,
                }]
            }
        else:
            # Slack format
            payload = {
                "text": f"*{title}*\n{message}",
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            if r.status_code >= 400:
                logger.warning("Webhook alert failed: %d %s", r.status_code, r.text)
    except Exception:
        logger.exception("Failed to send webhook alert")


async def _send_email(title: str, message: str):
    """Send email via SMTP."""
    try:
        smtp_host = await _get_setting("smtp_host")
        smtp_port = int(await _get_setting("smtp_port") or "587")
        smtp_user = await _get_setting("smtp_user")
        smtp_pass = await _get_setting("smtp_password")
        alert_email = await _get_setting("alert_email_to")

        if not all([smtp_host, smtp_user, smtp_pass, alert_email]):
            return

        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = alert_email
        msg["Subject"] = title
        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info("Email alert sent to %s", alert_email)
    except Exception:
        logger.exception("Failed to send email alert")


async def alert_backend_down(backend_name: str, host: str, port: int):
    await send_alert(
        "Backend Down",
        f"**{backend_name}** ({host}:{port}) is unreachable.",
        level="critical",
    )


async def alert_backend_recovered(backend_name: str, host: str, port: int):
    await send_alert(
        "Backend Recovered",
        f"**{backend_name}** ({host}:{port}) is back online.",
        level="info",
    )


async def alert_cert_expiring(hostname: str, days_left: int):
    await send_alert(
        "Certificate Expiring",
        f"**{hostname}** certificate expires in **{days_left} days**.",
        level="warning" if days_left > 3 else "critical",
    )


async def alert_cert_expired(hostname: str):
    await send_alert(
        "Certificate Expired",
        f"**{hostname}** certificate has **expired**!",
        level="critical",
    )
