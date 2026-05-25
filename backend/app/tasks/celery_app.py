from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure, task_revoked

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
    beat_schedule={},
)


@task_prerun.connect
def _on_task_prerun(task_id, task, args, kwargs, **_):
    from app.services.task_tracker import record_task, update_task_state, get_task
    if get_task(task_id) is None:
        record_task(task_id, task.name, kwargs or {})
    update_task_state(task_id, "STARTED")


@task_postrun.connect
def _on_task_postrun(task_id, task, args, kwargs, retval, state, **_):
    from app.services.task_tracker import update_task_state
    result = retval if isinstance(retval, dict) else ({"value": str(retval)} if retval is not None else None)
    update_task_state(task_id, state or "SUCCESS", result=result)


@task_failure.connect
def _on_task_failure(task_id, exception, **_):
    from app.services.task_tracker import update_task_state
    update_task_state(task_id, "FAILURE", result={"error": str(exception)})


@task_revoked.connect
def _on_task_revoked(request, **_):
    from app.services.task_tracker import update_task_state
    update_task_state(request.id, "REVOKED")
