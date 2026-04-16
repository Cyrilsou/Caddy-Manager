import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

logger = logging.getLogger(__name__)


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    from app.tasks.health_checker import run_health_checks
    from app.tasks.cert_checker import run_cert_checks
    from app.tasks.backup import run_backup
    from app.tasks.audit_cleanup import cleanup_old_audit_logs
    from app.core.metrics import update_business_metrics

    scheduler.add_job(
        run_health_checks,
        "interval",
        seconds=settings.HEALTH_CHECK_INTERVAL_SEC,
        id="health_checks",
        replace_existing=True,
    )

    scheduler.add_job(
        run_cert_checks,
        "interval",
        hours=settings.CERT_CHECK_INTERVAL_HOURS,
        id="cert_checks",
        replace_existing=True,
    )

    scheduler.add_job(
        update_business_metrics,
        "interval",
        seconds=60,
        id="metrics_update",
        replace_existing=True,
    )

    scheduler.add_job(
        run_backup,
        "cron",
        hour=3,
        minute=0,
        id="daily_backup",
        replace_existing=True,
    )

    scheduler.add_job(
        cleanup_old_audit_logs,
        "cron",
        hour=4,
        minute=0,
        id="audit_cleanup",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started: health %ds, certs %dh, metrics 60s, backup 03:00, audit cleanup 04:00",
                settings.HEALTH_CHECK_INTERVAL_SEC, settings.CERT_CHECK_INTERVAL_HOURS)
    return scheduler
