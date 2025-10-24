from apscheduler.schedulers.background import BackgroundScheduler
from app.storage import delete_expired_files


def start_cleaner(engine):
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: delete_expired_files(engine), "interval", hours=1)
    scheduler.start()
    return scheduler
