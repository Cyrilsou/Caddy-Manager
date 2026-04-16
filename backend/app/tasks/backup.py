import asyncio
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

BACKUP_DIR = os.environ.get("BACKUP_DIR", "/app/data/backups")


async def run_backup():
    """Run a PostgreSQL backup via pg_dump."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"caddypanel_{timestamp}.sql.gz")

    db_url = os.environ.get("DATABASE_URL", "")
    # Parse asyncpg URL to get connection details
    # postgresql+asyncpg://user:pass@host:port/dbname
    try:
        parts = db_url.replace("postgresql+asyncpg://", "").split("@")
        user_pass = parts[0].split(":")
        host_db = parts[1].split("/")
        host_port = host_db[0].split(":")

        pg_user = user_pass[0]
        pg_pass = user_pass[1] if len(user_pass) > 1 else ""
        pg_host = host_port[0]
        pg_port = host_port[1] if len(host_port) > 1 else "5432"
        pg_db = host_db[1] if len(host_db) > 1 else "caddypanel"
    except (IndexError, ValueError):
        logger.error("Could not parse DATABASE_URL for backup")
        return

    env = os.environ.copy()
    env["PGPASSWORD"] = pg_pass

    cmd = f"pg_dump -h {pg_host} -p {pg_port} -U {pg_user} {pg_db} | gzip > {backup_file}"

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode == 0:
            logger.info("Backup created: %s", backup_file)
            await _cleanup_old_backups()
        else:
            logger.error("Backup failed: %s", stderr.decode())
    except FileNotFoundError:
        logger.warning("pg_dump not found — skipping automated backup")
    except Exception:
        logger.exception("Backup failed")


async def _cleanup_old_backups(keep: int = 30):
    """Keep only the last N backups."""
    try:
        files = sorted(
            [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith(".sql.gz")],
            key=os.path.getmtime,
            reverse=True,
        )
        for old_file in files[keep:]:
            os.remove(old_file)
            logger.info("Removed old backup: %s", old_file)
    except Exception:
        logger.exception("Backup cleanup failed")
