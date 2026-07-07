# Phase 2: CI and Test Harness Reliability

## Objective

Make CI a trustworthy release gate. The workflow should run with valid runtime configuration, audit the actual project dependency graph, build frontend assets, build Docker, and execute tests with deterministic assumptions.

## Problems to Address

The CI test job currently sets `SECRET_KEY` to `test`, but the app requires a minimum length of 32 characters. That means tests that instantiate the app can fail at startup before meaningful assertions run. The agent guidance repeats a similarly short secret in local test commands. The security audit installs only `pip-audit` and runs `pip-audit --fail-on=all`, which may not audit the intended project dependencies in a deterministic way. The workflow has good breadth, but it needs to be checked against actual app startup requirements.

## Scope

This phase covers GitHub Actions, test environment variables, pytest configuration, dependency audit behavior, and minimal config smoke tests. It does not include broad application behavior changes except where needed to make tests accurately reflect production constraints.

## Implementation Steps

1. Replace all short test secrets in CI.

   Use a deterministic 32+ character value in every job that can import/create the app:

   ```yaml
   SECRET_KEY: test-secret-key-test-secret-key-1234
   ADMIN_PASSWORD: test-password-123
   ```

   Apply this to unit/integration tests, E2E tests, and any docs or agent instructions that show local test commands.

2. Standardize test environment in `tests/conftest.py` or a shared fixture.

   Ensure tests do not rely on module import order for setting `SECRET_KEY` and `ADMIN_PASSWORD`. If app config is imported at module import time, env vars must be set before importing app modules. Prefer a central test bootstrap that sets env defaults early.

3. Audit the actual project dependencies.

   Update the security-audit job to install and audit from requirements files in a clear way. Preferred:

   ```bash
   python -m pip install --upgrade pip
   pip install pip-audit
   pip-audit -r requirements.txt
   ```

   If dev dependencies should also be audited, add a separate step for `requirements-dev.txt`. Decide whether `--fail-on=all` is too strict for public CI. Strict is acceptable if dependency resolution is pinned enough to be stable.

4. Add or update dependency pinning strategy.

   The project currently uses version ranges. For public release, add one of:

   - `constraints.txt` generated from a known-good environment, used in CI installs.
   - Fully pinned `requirements.lock` for deployment.
   - A documented policy that range-pinned installs are tested weekly and release tags freeze known-good versions.

   Do not silently claim reproducible builds without a lock/constraints strategy.

5. Ensure frontend CI reflects production behavior.

   Keep `npm ci` and `npm run build`. If phase 5 moves Vite build into Docker, CI should still separately test frontend build and Docker image build.

6. Ensure Docker build CI catches asset requirements.

   After phase 5, add a lightweight Docker image inspection or startup test to confirm the built image contains either:

   - `app/static/dist/.vite/manifest.json`, if production requires Vite manifest; or
   - documented fallback assets sufficient for production.

7. Add smoke tests for startup config.

   Add tests for app creation with valid minimal env and no optional env values. Include empty optional env values where the deployment path injects them.

8. Review E2E job service startup.

   The workflow starts `docker compose up -d --profile production` and then waits for the `blog` service. Confirm the Compose service names and profiles match current configuration. Ensure failures print enough logs from `blog`, `celery`, `redis`, and `nginx` to debug release blockers.

## Tests to Add or Update

Add tests for:

- App creation succeeds with 32+ char `SECRET_KEY` and `ADMIN_PASSWORD`.
- App creation fails with short `SECRET_KEY` in a focused test, if that behavior is retained.
- Empty optional env vars do not override defaults after phase 1.
- CI commands shown in `AGENTS.md` and docs use valid secrets.

Update any fixture that hardcodes `SECRET_KEY=test`.

## Verification Commands

Run locally or in a branch CI run:

```bash
ruff check .
ruff format --check .
mypy app
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ --ignore=tests/e2e -v --cov=app --cov-fail-under=80
npm ci
npm run build
docker build .
pip-audit -r requirements.txt
```

If E2E is available:

```bash
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/e2e/ -v
```

## Acceptance Criteria

CI passes on a clean branch without relying on invalid test secrets. The audit job inspects project dependencies. Test commands in README/AGENTS/deployment docs are consistent. Docker and frontend jobs remain separate enough to isolate failures. Startup config tests cover the failure mode that previously made Compose fragile.

## Risks

Changing env bootstrap can mask real production validation if tests over-specialize behavior. Keep production validation active in tests unless a test explicitly disables it for a narrow reason. Avoid blanket `TESTING=true` shortcuts that skip security-critical startup checks.
