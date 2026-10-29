"""Celery application configuration."""

import os
from celery import Celery, Task
from flask import Flask, has_app_context

__all__ = ["celery_app", "init_celery"]

_worker_app: Flask | None = None


def _get_worker_app() -> Flask:
    """Return the Flask application used by tasks that run without one.

    The application is created once per process so a worker does not build a
    new application, database engine and connection pool for every task.
    """
    global _worker_app
    if _worker_app is None:
        from app import create_app

        _worker_app = create_app()
    return _worker_app


class ContextTask(Task):
    """Celery Task subclass that wraps execution in a Flask app context.

    An app context that is already active is reused, so the task shares the
    caller's application, database engine and session. A new app context is
    only created when the task runs outside of one, such as in a Celery
    worker process.
    """

    def __call__(self, *args, **kwargs):
        if has_app_context():
            return self.run(*args, **kwargs)

        with _get_worker_app().app_context():
            return self.run(*args, **kwargs)


def init_celery(app: Flask | None = None) -> Celery:
    """Initialize Celery with Flask app context."""
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
    else:
        celery_app.Task = ContextTask

    return celery_app


celery_app = init_celery()
