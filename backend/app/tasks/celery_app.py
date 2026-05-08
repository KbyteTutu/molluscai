from celery import Celery

from app.config import settings

celery_app = Celery(
    "malacoagent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        # "app.tasks.pdf_pipeline",
        # "app.tasks.ocr_task",
        # "app.tasks.metadata_task",
        # "app.tasks.embedding_task",
        # "app.tasks.taxon_verify",
        # "app.tasks.image_scraper",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)
