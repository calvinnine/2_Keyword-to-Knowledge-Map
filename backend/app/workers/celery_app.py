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
    # IMPORTANT: acks_late=True + automatic retries cause the same task to
    # run multiple times on transient failures (e.g. S2 429, worker SIGKILL).
    # That used to produce duplicate raw_payloads → UniqueViolation in the
    # next stage. We acknowledge tasks UP-FRONT (early-ack) and let failures
    # surface to the orchestration layer / user. Tasks must still be made
    # idempotent themselves (each task cleans its own state at start).
    task_acks_late=False,
    worker_prefetch_multiplier=1,
    # Disable automatic retries entirely; explicit pipeline re-enqueue is
    # how users re-run a failed job.
    task_default_retry_delay=30,
    task_max_retries=0,
)
