# Phase 4: Scheduler and Background Job Ownership

## Objective

Ensure scheduled jobs run exactly where intended in the supported production topology. The web app should not silently start independent APScheduler instances in every worker. Shutdown should not create a scheduler just to stop it. Documentation should distinguish web workers, Celery workers, and scheduler ownership clearly.

## Problems to Address

The app currently initializes APScheduler during app creation. The Dockerfile starts Granian with multiple workers. Each worker can therefore initialize its own scheduler. File locks reduce duplicate execution on one shared filesystem, but they do not remove scheduler contention, do not cover multi-host deployments, and do not make lifecycle ownership explicit.

`run.py` also has a separate lazy scheduler variable. The SIGTERM handler calls `_get_scheduler()`, which can initialize a scheduler during shutdown if that module-level variable is still `None`.

## Scope

This phase covers scheduler startup flags, production topology, shutdown lifecycle, scheduled-job docs, and tests. It does not replace APScheduler with Celery Beat unless that becomes simpler than explicit ownership.

## Target Design

Use an explicit environment variable to control in-process scheduler startup, for example:

```bash
ENABLE_SCHEDULER=false
```

Recommended defaults:

- Local `python run.py`: scheduler enabled by default or enabled through setup docs, depending on developer ergonomics.
- Production web container: scheduler disabled by default.
- Dedicated scheduler container/profile or one explicitly configured process: scheduler enabled.
- Celery worker: scheduler disabled unless it is intentionally the scheduler owner.

If the project prefers no new service, production docs can recommend `--workers 1` plus `ENABLE_SCHEDULER=true` for small deployments. However, the default Dockerfile should not combine multiple web workers with implicit scheduler startup.

## Implementation Steps

1. Add scheduler config variables.

   Add parsed config in `app/config.py`:

   ```python
   ENABLE_SCHEDULER = _env_bool("ENABLE_SCHEDULER", default=False)
   SCHEDULER_ROLE = _env_str("SCHEDULER_ROLE", "web")
   ```

   A single boolean is probably sufficient. Keep role naming only if it helps docs or future extension.

2. Gate scheduler initialization in `create_app()`.

   Replace unconditional `init_scheduler(app)` with:

   ```python
   if ENABLE_SCHEDULER:
       init_scheduler(app)
   else:
       app.logger.info("APScheduler disabled; set ENABLE_SCHEDULER=true to run scheduled jobs")
   ```

   Ensure tests can assert scheduler disabled without importing APScheduler unnecessarily.

3. Make scheduler initialization idempotent.

   In `app.scheduler.init_scheduler`, if `_scheduler` exists and is running, return it instead of starting another instance. This protects accidental repeated calls in the same process.

4. Fix shutdown lifecycle.

   Remove `run.py`'s separate `_scheduler` state or make it query the scheduler module without creating a new scheduler. Add a function in `app.scheduler`, for example `shutdown_scheduler(wait: bool = True)`, that only shuts down the existing scheduler if present.

   The SIGTERM handler should call `shutdown_scheduler(wait=True)` and must never call a function that starts the scheduler.

5. Decide how scheduled jobs run in Docker Compose.

   Preferred option: add a dedicated `scheduler` service using the same image and command that runs a small scheduler entrypoint with `ENABLE_SCHEDULER=true` and no web server. This is clean but requires an entrypoint script.

   Simpler option: keep a single `blog` web container with `--workers 1` if `ENABLE_SCHEDULER=true`. If the Dockerfile remains at four workers, default `ENABLE_SCHEDULER=false` and document that scheduled publish/newsletter/backups require enabling a scheduler owner.

   Do not leave the current implicit multi-worker scheduler behavior as the documented production default.

6. Reconcile Celery and APScheduler responsibilities.

   The Compose file says Celery handles newsletters, webhook delivery, image variants, and backups. APScheduler currently triggers daily newsletter, cleanup, scheduled publish, and daily backup. Clarify which layer owns triggering versus execution:

   - APScheduler/cron can trigger jobs.
   - Celery should execute long-running jobs when available.
   - Web request workers should not run long scheduled work by accident.

7. Update health reporting.

   If scheduler status is exposed in `/health`, ensure it reports disabled distinctly from unhealthy. Suggested states: `running`, `disabled`, `stopped`, `error`.

8. Update docs.

   Update README, DEPLOY.md, AGENTS.md, Docker comments, and `.env.example` with `ENABLE_SCHEDULER`. Include a short warning: exactly one scheduler owner per deployment.

## Tests to Add or Update

- App creation with `ENABLE_SCHEDULER=false` does not start scheduler.
- App creation with `ENABLE_SCHEDULER=true` starts scheduler once.
- Repeated `init_scheduler(app)` calls in the same process return the same scheduler or do not duplicate jobs.
- `shutdown_scheduler()` does not start a scheduler when none exists.
- Health output distinguishes disabled from failed scheduler.

## Verification Commands

```bash
ruff check .
ruff format --check .
mypy app
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ -v --ignore=tests/e2e -k "scheduler or health"
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 ENABLE_SCHEDULER=false python -m pytest tests/ -v --ignore=tests/e2e
```

Manual Docker checks:

```bash
# Scheduler disabled web stack should start cleanly.
docker compose --profile production up -d --build
docker compose logs blog --tail=100 | grep -i scheduler

# Scheduler-enabled owner should log exactly one owner if a scheduler service is added.
docker compose logs scheduler --tail=100
```

## Acceptance Criteria

The production web service no longer starts APScheduler implicitly in every worker. There is a documented way to run exactly one scheduler owner. Shutdown never initializes a new scheduler. Tests cover disabled/enabled scheduler startup and idempotence. Deployment docs no longer imply that multi-worker in-process scheduling is a safe general production default.

## Risks

Disabling scheduler by default can surprise existing users who rely on scheduled publishing/newsletters/backups. Mitigate by documenting the new flag prominently and adding startup logs that state whether scheduler is enabled. Consider preserving local development behavior if that avoids friction, but keep production explicit.
