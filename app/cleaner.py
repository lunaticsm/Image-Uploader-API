from apscheduler.schedulers.background import BackgroundScheduler

from app.storage import delete_expired_files


def start_cleaner(engine, metrics, logger):
    scheduler = BackgroundScheduler()

    def _job():
        deleted = delete_expired_files(engine)
        if deleted:
            metrics.record_deletions(deleted)
            logger.info("event=cleanup_deleted count=%s", deleted)

    scheduler.add_job(_job, "interval", hours=1)
    scheduler.start()
    return scheduler
