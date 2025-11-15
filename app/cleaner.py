from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.exc import OperationalError

from app.storage import delete_expired_files


def start_cleaner(engine, metrics, logger):
    scheduler = BackgroundScheduler()

    def _job():
        try:
            deleted = delete_expired_files(engine)
            if deleted:
                metrics.record_deletions(deleted)
                logger.info("event=cleanup_deleted count=%s", deleted)
        except OperationalError as e:
            logger.error("Database connection error in cleanup job: %s", str(e))
            # The delete_expired_files function already has retry logic, if this still fails,
            # we log the error but don't want to crash the scheduler
        except Exception as e:
            logger.error("Unexpected error in cleanup job: %s", str(e))

    scheduler.add_job(_job, "interval", hours=1)
    scheduler.start()
    return scheduler
