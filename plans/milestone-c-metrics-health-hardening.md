# Milestone C Plan: Metrics and Health Hardening

## Objective

Prevent accidental public exposure of operational data while preserving a simple public basic health endpoint for Docker health checks and uptime monitoring.

The current `/health` endpoint has a reasonable split between basic and detailed modes, but detailed mode depends on `HEALTH_CHECK_SECRET` only when configured. The current `/metrics` endpoint is public if neither `METRICS_SECRET` nor `HEALTH_CHECK_SECRET` is configured. For a public-release self-hosted CMS, metrics should fail closed in production unless explicitly enabled and authenticated.

## Current behavior to review

Relevant files:

- `app/routes/public/meta.py`
- `app/config.py`
- `docker-compose.yml`
- `.env.example`
- `README.md`
- `DEPLOY.md`
- `tests/*health*`
- `tests/*metrics*`

Current behavior:

- Basic `/health` performs a database check and scheduler status check and returns JSON suitable for Docker health checks.
- Detailed `/health?detailed=true` performs database, scheduler, search, disk, integrity, redis, celery, and backup freshness checks.
- Detailed health only requires a secret if `HEALTH_CHECK_SECRET` is configured.
- `/metrics` uses `METRICS_SECRET` or `HEALTH_CHECK_SECRET` if either is configured, but is public if neither exists.

## Target behavior

### Basic health

Basic `/health` should remain unauthenticated and safe. It should disclose only coarse status necessary for health checks.

Acceptable basic response:

```json
{
  "status": "ok",
  "checks": {
    "database": "ok",
    "scheduler": "disabled"
  },
  "timestamp": "..."
}
```

Do not include sensitive paths, detailed error messages, backup names, Redis URLs, Celery internals, secrets, or host configuration.

### Detailed health

Detailed health should require authentication in production. Authentication should prefer a header and may preserve query-string compatibility for existing users.

Recommended accepted auth forms:

- `Authorization: Bearer <HEALTH_CHECK_SECRET>`
- `X-Health-Secret: <HEALTH_CHECK_SECRET>`
- Deprecated compatibility: `?secret=<HEALTH_CHECK_SECRET>`

If `FLASK_ENV=production` and detailed health is requested without a configured secret, the endpoint should return `403` or a generic disabled response rather than exposing details.

### Metrics

Metrics should require explicit enablement and authentication in production.

Recommended config:

- `ENABLE_METRICS=false` by default.
- `METRICS_SECRET` must be set when `ENABLE_METRICS=true` in production.
- If `ENABLE_METRICS=false`, `/metrics` returns `404` or `403`.
- If `ENABLE_METRICS=true` but no secret is configured in production, app startup should fail or metrics route should fail closed with a startup warning. Prefer startup failure for security clarity.

Recommended auth forms:

- `Authorization: Bearer <METRICS_SECRET>`
- `X-Metrics-Secret: <METRICS_SECRET>`
- Deprecated compatibility: `?secret=<METRICS_SECRET>`

Do not fall back to public metrics.

## Implementation steps

### Step 1: Add configuration flags

In `app/config.py`, add explicit config parsing:

```python
ENABLE_METRICS = _env_bool("ENABLE_METRICS", default=False)
```

Add `ENABLE_METRICS` to `__all__`.

Retain `METRICS_SECRET` and `HEALTH_CHECK_SECRET`.

Consider adding helpers:

```python
def is_production() -> bool:
    return os.environ.get("FLASK_ENV") == "production"
```

or keep inline checks if the codebase does not use config classes.

### Step 2: Implement shared secret-check helper

In `app/routes/public/meta.py`, add a small helper to avoid duplicating auth parsing.

Recommended shape:

```python
def _provided_secret(header_name: str) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.removeprefix("Bearer ").strip()
    return request.headers.get(header_name, "") or request.args.get("secret", "")


def _secret_matches(expected: str, header_name: str) -> bool:
    if not expected:
        return False
    provided = _provided_secret(header_name)
    return bool(provided) and hmac.compare_digest(provided, expected)
```

Use separate header names for health and metrics.

### Step 3: Harden detailed health

Change detailed health logic:

- If `detailed=true` and `HEALTH_CHECK_SECRET` is set, require a matching secret.
- If `detailed=true`, `HEALTH_CHECK_SECRET` is unset, and production mode is active, return `403` with a generic error.
- In development, allow unauthenticated detailed health only if preserving current developer ergonomics is desired. Document that this is development-only.

Avoid revealing whether a secret exists beyond a generic unauthorized/disabled response.

### Step 4: Harden metrics

Change `/metrics` logic:

- If `ENABLE_METRICS` is false, return `404` or `403`. Use `404` if the project prefers not to advertise the endpoint; use `403` if operational clarity is preferred.
- If `ENABLE_METRICS` is true and production mode is active, require `METRICS_SECRET`. If absent, fail startup during app creation or return `503` with generic text. Startup failure is preferable because misconfiguration should be caught immediately.
- If `ENABLE_METRICS` is true and not production, allow unauthenticated metrics only if explicitly documented.
- If `METRICS_SECRET` is set, require it regardless of environment.

Do not use `HEALTH_CHECK_SECRET` as a fallback for metrics unless this is retained for backward compatibility with a deprecation note. Prefer independent secrets.

### Step 5: Add startup validation

In `create_app()` or config validation:

- If `FLASK_ENV=production` and `ENABLE_METRICS=true` and `METRICS_SECRET` is empty, raise `RuntimeError`.
- If detailed health is configured in a way that might expose details publicly, warn or fail. Since detailed health is request-driven, requiring `HEALTH_CHECK_SECRET` only when detailed mode is used may be enough; however docs should strongly recommend setting it.

### Step 6: Update Docker and env docs

Update `.env.example`:

```env
# Metrics are disabled by default. To expose Prometheus metrics in production,
# set ENABLE_METRICS=true and METRICS_SECRET to a strong random value.
ENABLE_METRICS=false
METRICS_SECRET=
HEALTH_CHECK_SECRET=
```

Update `docker-compose.yml` environment block to include `ENABLE_METRICS=${ENABLE_METRICS:-false}` if appropriate.

Update README/DEPLOY monitoring sections:

- Basic health path.
- Detailed health auth examples.
- Metrics enablement and auth examples.
- Reverse proxy advice to keep metrics internal where possible.

### Step 7: Add tests

Add focused tests around `app.routes.public.meta` behavior.

Test cases:

1. `GET /health` returns 200 without secret.
2. `GET /health?detailed=true` returns unauthorized/forbidden in production when `HEALTH_CHECK_SECRET` is configured and no secret is provided.
3. `GET /health?detailed=true` succeeds with `Authorization: Bearer <secret>`.
4. `GET /health?detailed=true` succeeds with `X-Health-Secret`.
5. Query-string secret compatibility works if retained.
6. `GET /metrics` returns 404/403 when `ENABLE_METRICS=false`.
7. Production app startup fails if `ENABLE_METRICS=true` and `METRICS_SECRET` is unset.
8. `GET /metrics` returns 401/403 with metrics enabled but no secret provided.
9. `GET /metrics` succeeds with valid bearer/header auth.
10. Invalid secret fails using constant-time comparison path.

Use monkeypatching or app factory fixtures to isolate environment variables.

## Security considerations

Do not put secrets in examples that look reusable. Use placeholders and generation commands.

Prefer headers over query-string secrets because query strings are more likely to appear in access logs, browser history, proxy logs, and monitoring tools. Keep query-string support only if backward compatibility is necessary and mark it deprecated in docs.

Do not expose detailed backend error messages from health endpoints. Application logs can retain details; public JSON should use status strings.

## Backward compatibility

This milestone may break users who currently scrape `/metrics` without authentication. That is acceptable for a pre-public-release hardening pass, but document the change in release notes if a changelog exists.

If minimizing breakage matters, use a transition mode:

- In development, public metrics allowed only when `ENABLE_METRICS=true`.
- In production, authenticated metrics required.

## Validation commands

Run:

```bash
python -m pytest tests/ --ignore=tests/e2e -v
python -m pytest tests/ -k "health or metrics" -v
ruff check app tests
ruff format --check app tests
mypy app/
docker compose --profile production config
```

If Docker smoke tests are available:

```bash
docker compose --profile production up -d --build
curl -f http://127.0.0.1:5000/health
curl -i http://127.0.0.1:5000/metrics
docker compose --profile production down -v
```

## Acceptance criteria

- Basic `/health` remains unauthenticated and Docker-compatible.
- Detailed health requires authorization in production.
- `/metrics` is disabled by default.
- Metrics cannot be publicly exposed in production without explicit enablement and a configured secret.
- Header-based auth works for both detailed health and metrics.
- Tests cover enabled, disabled, authorized, and unauthorized paths.
- README, DEPLOY.md, `.env.example`, and Compose environment variables document the new behavior.

## Suggested commit scope

This milestone should include code, tests, and docs together. Do not include broader deployment topology rewrites unless Milestone A/B have not yet landed; in that case, keep only the minimum docs needed to describe metrics and health safely.
