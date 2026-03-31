"""Configuración de la aplicación Celery."""

from celery import Celery

from core.config import settings

celery_app = Celery(
    "openclinica",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "api.v1.ia.scribe.worker_transcripcion",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Argentina/Buenos_Aires",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_routes={
        "scribe.transcribir_audio": {"queue": "transcripcion"},
    },
)
