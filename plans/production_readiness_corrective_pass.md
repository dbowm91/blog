# Production Readiness Corrective Pass

## Context

The production-readiness roadmap has now been implemented across eight follow-up commits. The repository is materially stronger than the pre-roadmap state: deployment config fallback handling, CI secrets, CSRF/API separation, scheduler ownership, Docker frontend asset building, backend support scoping, release documentation, and security/observability all received targeted work.

A post-implementation source review still found several release-blocking or release-polish issues. This corrective pass is intentionally narrow. It should not restart broad architectural work. It should close the gaps that keep the repo from being a credible public release candidate.

## Current Assessment

The repo is near release-candidate shape, but not yet release-ready. The remaining concerns are:

1. Local setup documentation still implies `.env` variables loaded by `./setup.sh` persist into the parent shell, which is not true when the script is executed normally.
2. `config.toml` is still tracked while `.gitignore` now ignores it, and it still contains operator-specific author identity and Gmail SMTP defaults.
3. API scoped-token enforcement appears incomplete across update/delete and non-post write endpoints.
4. `/health` performs expensive detailed diagnostics on the basic Docker health path.
5. `/metrics` documentation/config naming is inconsistent: the route mentions `METRICS_SECRET` but checks `HEALTH_CHECK_SECRET`.
6. GitHub Actions Compose E2E startup may not receive `SECRET_KEY` and `ADMIN_PASSWORD` before `docker compose up`.
7. `pyproject.toml` claims `Development Status :: 5 - Production/Stable` before verified CI/Docker closure.
8. CI status for the latest commit was not visible during review, so green status must be established rather than assumed.

## Scope

This plan covers one corrective pass to address the above issues and run final verification. It should produce one PR or one compact sequence of commits. Avoid broad refactors, visual redesigns, or optional feature expansion.

## Phase A: Fix Local Setup and Environment Loading

### Problem

`setup.sh` sources `.env` inside the script, then prints `python run.py`. Environment variables exported inside an executed child script do not persist into the parent shell. The README says setup creates credentials and loads `.env`, which can mislead users into running `python run.py` without `SECRET_KEY` and `ADMIN_PASSWORD` in the environment.

### Preferred Fix

Add `python-dotenv` to runtime dependencies and load `.env` before `app.config` is imported.

Implementation guidance:

1. Add `python-dotenv>=1.0,<2.0` to `requirements.txt`.
2. In `run.py`, before `from app import create_app`, call:

   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

3. For any CLI or Celery entrypoint that can import `app.config` without going through `run.py`, add an early dotenv load in a shared bootstrap location or in `app/config.py` before `_config = load_config()` and before reading env vars. If using `app/config.py`, handle missing dependency only if it remains optional; if `python-dotenv` is runtime dependency, import directly.
4. Keep `setup.sh` simple: create `.env`, create/copy `config.toml`, and print `python run.py`. Do not claim that script-side `source .env` persists. It can still source for immediate script-internal validation if useful, but docs must not rely on that.

### Alternative Fix

If avoiding a new dependency, update README and setup output to instruct users to run:

```bash
source venv/bin/activate
set -a
source .env
set +a
python run.py
```

This is more brittle. Prefer dotenv.

### Tests / Verification

Add or update a test that runs app creation after writing a temporary `.env` if the app-level dotenv path is testable. At minimum manually verify:

```bash
rm -rf venv .env config.toml instance logs
./setup.sh --dev
python run.py
```

Expected: app starts without manually exporting `SECRET_KEY` or `ADMIN_PASSWORD`.

## Phase B: Remove or Normalize Tracked `config.toml`

### Problem

`.gitignore` now ignores `config.toml`, and `config.toml.example` exists, but `config.toml` remains tracked. It includes operator-specific author values and Gmail SMTP defaults. This is inconsistent and unsuitable for public release.

### Preferred Fix

Remove tracked `config.toml` from the repository and keep only `config.toml.example`.

Implementation guidance:

1. Delete tracked `config.toml` with `git rm config.toml` or the GitHub delete API equivalent.
2. Confirm `.gitignore` contains `config.toml`.
3. Ensure `setup.sh` copies `config.toml.example` to `config.toml` if absent.
4. Ensure Docker builds still work after deleting tracked `config.toml`. If Docker runtime needs `config.toml`, either:
   - Copy `config.toml.example` to `config.toml` during Docker build; or
   - Modify `app.config.load_config()` to fall back to `config.toml.example` when `config.toml` is missing and the app is running in a container/default mode.

Preferred runtime behavior: `load_config()` should load `config.toml` if present; otherwise load `config.toml.example` with a clear log/warning. Do not require an untracked file for Docker image startup unless Compose explicitly mounts/provides it.

### Tests / Verification

Run from a clean checkout with no `config.toml`:

```bash
python -m pytest tests/test_config.py -v
npm ci
npm run build
docker build -t devlog:config-smoke .
docker run --rm -e SECRET_KEY=test-secret-key-test-secret-key-1234 -e ADMIN_PASSWORD=test-password-123 devlog:config-smoke python -c "from app import create_app; create_app(); print('ok')"
```

Expected: app starts using example defaults or setup-created local config.

## Phase C: Complete API Scope Enforcement Audit

### Problem

`POST /api/posts` now requires `posts:write`, but post update and delete still appear to require only `require_api_key`. Other write endpoints may also be missing their matching `require_scope` decorator.

### Implementation Steps

1. Inventory all API routes under `app/routes/api/`.
2. Create a route-to-scope table in tests or docs.
3. Apply `require_scope(...)` consistently to all mutating endpoints.

Expected mapping:

- Post create/update/delete: `posts:write`.
- Post read/list: `posts:read` if scoped reads are enforced, or legacy full API key if intentionally broad.
- Page create/update/delete: `pages:write`.
- Page read/list: `pages:read` if scoped reads are enforced.
- Series create/update/delete: `series:write`.
- Series read/list: `series:read` if scoped reads are enforced.
- Tag create/update/delete or mutation endpoints: `tags:write`.
- Tag read/list: `tags:read` if scoped reads are enforced.
- Subscriber mutation endpoints: `subscribers:write`.
- Subscriber read/list/export: `subscribers:read`.
- Newsletter send: `newsletter:send`.
- Analytics/stats endpoints: `analytics:read`.
- Media read/write endpoints, if present: `media:read` / `media:write`.

4. Preserve legacy `API_KEY` behavior if that is intended to represent full-scope admin API access. Scoped token behavior should still be enforced for scoped tokens.
5. Add tests for every mutating endpoint that prove a token missing the required scope receives 403.
6. Add positive tests proving valid scopes work.

### Tests / Verification

```bash
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ -v --ignore=tests/e2e -k "api and scope"
```

Also run the full non-E2E suite after adding decorators because route tests often share fixtures:

```bash
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ --ignore=tests/e2e -v --cov=app --cov-fail-under=80
```

## Phase D: Split Cheap Health from Detailed Diagnostics

### Problem

`/health` currently performs multiple checks on every request, including SQLite `PRAGMA integrity_check`, Redis ping, Celery inspect, backup freshness, FTS check, disk check, and DB check. Docker and reverse proxies use this endpoint as a frequent liveness/readiness probe. Expensive checks can create self-inflicted load or false negatives.

### Target Behavior

Basic `/health` should be cheap and safe for frequent polling:

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

Detailed diagnostics should require `?detailed=true&secret=...` when `HEALTH_CHECK_SECRET` is configured. Detailed mode can include FTS, disk, DB integrity, Redis, Celery, backup freshness, latency, scheduler next run, etc.

### Implementation Steps

1. Keep the basic DB `SELECT 1` check in all modes.
2. Keep scheduler status in all modes if it is cheap.
3. Move the following into detailed mode only:
   - `PRAGMA integrity_check`
   - Redis ping
   - Celery inspect
   - Backup freshness filesystem scan
   - FTS table existence check, unless known cheap enough and desired in readiness
   - Disk usage check, unless known cheap enough and desired in readiness
4. If `detailed=true` is requested without valid secret when `HEALTH_CHECK_SECRET` is configured, return only basic health or return 401 for detailed. Pick one behavior and document it. Preferred: return 401 for unauthorized detailed diagnostics.
5. Update Docker healthcheck docs to clarify it uses basic mode.
6. Add tests for basic vs detailed output.

### Tests / Verification

```bash
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ -v --ignore=tests/e2e -k "health"
```

Manual checks:

```bash
curl -f http://localhost:5000/health
curl -i "http://localhost:5000/health?detailed=true"
curl -i "http://localhost:5000/health?detailed=true&secret=$HEALTH_CHECK_SECRET"
```

## Phase E: Fix Metrics Secret Naming and Access Control

### Problem

The `/metrics` route docstring says `METRICS_SECRET`, but implementation checks `HEALTH_CHECK_SECRET`. That mismatch will confuse operators.

### Preferred Fix

Add a real `METRICS_SECRET` environment variable and document fallback behavior.

Recommended behavior:

1. Add `METRICS_SECRET = _env_str("METRICS_SECRET", "")` to `app/config.py` and `__all__`.
2. In `/metrics`, require `METRICS_SECRET` when set.
3. Do not reuse `HEALTH_CHECK_SECRET` implicitly unless deliberately documented as a fallback. If using fallback, prefer:

   ```python
   secret_required = METRICS_SECRET or HEALTH_CHECK_SECRET
   ```

   and document that `METRICS_SECRET` takes precedence.
4. Add `METRICS_SECRET` to `.env.example`, DEPLOY.md, README env var table, SECURITY.md monitoring section, and AGENTS.md.
5. Add tests for unauthenticated metrics with no secret, unauthorized metrics with configured secret, and authorized metrics with secret.

### Verification

```bash
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ -v --ignore=tests/e2e -k "metrics"
```

## Phase F: Fix CI Compose Environment Injection

### Problem

The E2E job runs `docker compose up -d --profile production` before setting `SECRET_KEY` and `ADMIN_PASSWORD` in the pytest step. Compose requires those env vars during service startup. Unless the runner environment already has them, Compose can fail before tests run.

### Implementation Steps

1. Add env vars directly to the `Start services` step:

   ```yaml
   - name: Start services
     env:
       SECRET_KEY: test-secret-key-test-secret-key-1234
       ADMIN_PASSWORD: test-password-123
       SESSION_COOKIE_SECURE: "false"
     run: docker compose up -d --profile production
   ```

2. Add the same env vars to `Wait for blog to be healthy` and `Cleanup` if Compose interpolation needs them for subsequent commands.
3. Alternatively, generate a CI `.env` file before Compose startup:

   ```bash
   cat > .env <<'EOF'
   SECRET_KEY=test-secret-key-test-secret-key-1234
   ADMIN_PASSWORD=test-password-123
   SESSION_COOKIE_SECURE=false
   EOF
   ```

   This is often the most robust Compose path.
4. Ensure E2E tests target the correct host/port exposed by Compose/nginx. If using nginx ports 80/443, verify tests are configured accordingly. If tests target Flask directly, expose/bind blog port in CI or adjust test config.
5. Confirm `docker compose wait blog` is supported on the installed Compose version. If unreliable, replace with an explicit curl readiness loop.

### Verification

A GitHub Actions run is the real verification. Locally:

```bash
SECRET_KEY=test-secret-key-test-secret-key-1234 ADMIN_PASSWORD=test-password-123 SESSION_COOKIE_SECURE=false docker compose --profile production up -d --build
docker compose ps
docker compose logs blog --tail=100
curl -f http://localhost/health || curl -f http://localhost:5000/health
docker compose --profile production down -v
```

## Phase G: Adjust Release Classifier Until Closure Is Verified

### Problem

`pyproject.toml` declares `Development Status :: 5 - Production/Stable` before this closure pass and CI verification are complete.

### Implementation Steps

1. Change classifier to `Development Status :: 4 - Beta` for the corrective PR.
2. Add a note in `RELEASE.md` that the classifier may be moved to stable only after:
   - CI passes on main.
   - Docker Compose smoke passes from a clean checkout.
   - Backup/restore smoke passes.
   - Public docs no longer contain known setup/config mismatches.
3. Optionally bump back to stable in the final release commit/tag PR.

## Phase H: Final Verification Gate

After Phases A-G, run the full quality gate.

### Required Commands

```bash
ruff check .
ruff format --check .
mypy app
npm ci
npm run build
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ --ignore=tests/e2e -v --cov=app --cov-fail-under=80
pip-audit -r requirements.txt --fail-on=all
docker build -t devlog:release-candidate .
docker run --rm devlog:release-candidate test -f /app/app/static/dist/.vite/manifest.json
```

### Docker Runtime Smoke

```bash
docker run -d --name devlog-rc \
  -e SECRET_KEY=test-secret-key-test-secret-key-1234 \
  -e ADMIN_PASSWORD=test-password-123 \
  -e SESSION_COOKIE_SECURE=false \
  -p 5000:5000 \
  devlog:release-candidate

for i in $(seq 1 30); do
  curl -sf http://localhost:5000/health && break
  sleep 2
done

docker logs devlog-rc --tail=100
docker rm -f devlog-rc
```

### Compose Smoke

```bash
cat > .env <<'EOF'
SECRET_KEY=test-secret-key-test-secret-key-1234
ADMIN_PASSWORD=test-password-123
SESSION_COOKIE_SECURE=false
ENABLE_SCHEDULER=false
EOF

docker compose --profile production up -d --build
docker compose ps
curl -f http://localhost/health || curl -f http://localhost:5000/health
docker compose --profile production down -v
```

### Manual Browser/API Smoke

1. Fresh local setup starts without manual env export if dotenv path is implemented.
2. Admin login works.
3. Admin logout works with valid CSRF.
4. Create/edit/publish post.
5. Submit and moderate a comment.
6. Upload media.
7. API create/update/delete post works with valid scope.
8. API mutating routes fail with 403 when scoped token lacks required scope.
9. `/health` basic response is cheap and small.
10. `/health?detailed=true&secret=...` includes detailed diagnostics.
11. `/metrics` auth behavior matches docs.

## Files Likely to Change

- `requirements.txt`
- `run.py`
- `app/config.py`
- `app/routes/public/meta.py`
- `app/routes/api/*.py`
- `.github/workflows/ci.yml`
- `setup.sh`
- `README.md`
- `DEPLOY.md`
- `SECURITY.md`
- `RELEASE.md`
- `AGENTS.md`
- `.env.example`
- `pyproject.toml`
- `tests/test_config.py`
- `tests/test_csrf_api_auth.py`
- `tests/test_security.py` or a new `tests/test_health_metrics.py`
- API route tests for scoped tokens
- Delete tracked `config.toml`

## Acceptance Criteria

This corrective pass is complete when:

1. Fresh local setup works exactly as documented.
2. Tracked `config.toml` is removed or made fully generic and policy-consistent.
3. All mutating scoped-token API routes enforce the correct scope.
4. Basic `/health` is cheap; detailed diagnostics are gated.
5. `/metrics` secret behavior and docs are consistent.
6. CI Compose startup supplies required env vars before `docker compose up`.
7. The project no longer claims stable classifier status until final validation is complete.
8. Full tests, lint, typecheck, frontend build, Docker build, and Docker/Compose smoke checks pass.
9. The latest main commit has visible passing GitHub Actions status before public release.
