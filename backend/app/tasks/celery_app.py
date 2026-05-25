from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "molluscai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.auction_scraper",
        "app.tasks.image_downloader",
        "app.tasks.embedding_job",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=None,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "scrape-auctions-hourly": {
            "task": "auction.scrape_incremental",
            "schedule": crontab(minute=15),
            "kwargs": {"batch_size": 200},
        },
        "download-sold-images-half-hourly": {
            "task": "auction.download_images",
            "schedule": crontab(minute="*/30"),
            "kwargs": {"batch_size": 50},
        },
        # Embed tasks are disabled by default — enable via Admin → Settings.
        # "embed-taxa-hourly": {
        #     "task": "taxa.embed_run",
        #     "schedule": crontab(minute=5, hour="*/2"),
        #     "kwargs": {"rebuild": False},
        # },
        # "embed-auctions-daily": {
        #     "task": "auction.embed_run",
        #     "schedule": crontab(minute=30, hour="*/4"),
        #     "kwargs": {"rebuild": False},
        # },
    },
)
