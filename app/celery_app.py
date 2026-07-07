"""Celery application configuration."""

from celery import Celery
from flask import Flask

__all__ = ["celery_app", "init_celery"]


def init_celery(app: Flask | None = None) -> Celery:
    """Initialize Celery with Flask app context."""
    import os

    broker_url = os.environ.get("CELERY_BROKER_URL") or os.environ.get(
        "REDIS_URL", "redis://localhost:6379/0"
    )

    celery_app = Celery(
        "blog",
        broker=broker_url,
        backend=broker_url,
        include=["app.tasks"],
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,
        task_soft_time_limit=240,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=100,
    )

    if app:
        celery_app.conf.update(
            task_acks_late=True,
            task_reject_on_worker_lost=True,
        )

    return celery_app


celery_app = init_celery()
