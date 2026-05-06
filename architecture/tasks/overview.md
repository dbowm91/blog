# Task Processing

The blog uses two task processing systems:

| System | File | Purpose |
|--------|------|---------|
| Celery | `app/celery_app.py`, `app/tasks.py` | Async task queue (Redis broker) |
| APScheduler | `app/scheduler.py` | In-process scheduled jobs |

## See Also
- [Celery Tasks](tasks/celery-tasks.md) - Async task definitions
- [APScheduler](tasks/scheduler.md) - Scheduled jobs
