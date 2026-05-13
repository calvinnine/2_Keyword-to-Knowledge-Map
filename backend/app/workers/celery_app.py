from celery import Celery

from app.config import settings

celery_app = Celery(
    "k2km",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.collect",
        "app.workers.tasks.process",
        "app.workers.tasks.analyze",
        "app.workers.tasks.pipeline",
        "app.workers.tasks.ntis_overlay",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=30,
    task_max_retries=3,
)
