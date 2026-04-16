import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

logger = logging.getLogger(__name__)


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    from app.tasks.health_checker import run_health_checks
    from app.tasks.cert_checker import run_cert_checks

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

    scheduler.start()
    logger.info("Scheduler started: health checks every %ds, cert checks every %dh",
                settings.HEALTH_CHECK_INTERVAL_SEC, settings.CERT_CHECK_INTERVAL_HOURS)
    return scheduler
