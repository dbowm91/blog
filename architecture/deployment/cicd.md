# CI/CD (`.github/workflows/`)

GitHub Actions workflows for testing and deployment.

## Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | push to `main`, pull_request, weekly schedule (Mondays 08:00 UTC) | Full test suite and release gates |
| `release.yml` | push of a `v*` tag | Builds and publishes the wheel, sdist, Docker bundle and `checksums.txt` |
| `installer-smoke.yml` | push to `main`, pull_request | Builds release artifacts and exercises `scripts/install.sh` (native install, Docker bundle extraction, dry run) and runs ShellCheck on the installer |
| `test.yml` | push, pull_request | A minimal pytest run without the coverage gate |

## ci.yml Jobs

`ci.yml` defines eleven jobs.

### 1. lint-and-type
- **Tool**: `ruff` (linting and format check), `mypy` (type checking)
- **Python**: 3.12

### 2. test
- **Tool**: `pytest` with coverage
- **Coverage**: Minimum 80%
- **Python**: 3.12 (single-version matrix)
- **Database**: SQLite

### 3. theme-policy
- **Tool**: `python scripts/theme_accessibility_report.py --strict`
- **Purpose**: Every bundled theme translates and has no unexpected mandatory accessibility failure

### 4. migration-chain
- **Tool**: `python -m pytest tests/test_migration_chain.py tests/test_migration_drop_theme_preset.py -v`
- **Purpose**: The Halloy migration revisions apply, downgrade and re-apply cleanly
- **Depends on**: `test`

### 5. theme-package-verification
- **Tool**: `python -m build` then `python scripts/verify_theme_package.py dist/*.whl`
- **Purpose**: The built wheel carries the packaged theme resources

### 6. frontend-build
- **Tool**: Node.js 20, `npm ci` + `npm run build`
- **Purpose**: Build frontend assets

### 7. security-audit
- **Tool**: `pip-audit`
- **Purpose**: Vulnerability scanning
- **Mode**: `--fail-on=all` (strict mode — fails on any known vulnerability, including informational)

### 8. docker-build
- **Tool**: `docker build .`
- **Purpose**: Verify the Dockerfile builds successfully and the resulting image contains the frontend assets
- **Steps**:
  1. Builds the image with tag `devlog:ci`
  2. Verifies `app/static/dist/.vite/manifest.json` exists in the image (confirms the frontend builder stage produced assets)

This job validates the multi-stage build pipeline: Node.js frontend build → Python dependency install → runtime image assembly.

### 9. e2e-tests
- **Tool**: Playwright
- **Environment**: Docker-based with `--profile production`
- **Browser**: Chromium
- **Compose files**: `docker-compose.yml` + `docker-compose.ci.yml` (CI override publishes port 5000)
- **Base URL**: Configured via `E2E_BASE_URL` env var (default: `http://localhost:5000` in CI)
- **Depends on**: `test`, `docker-build`
- **Failure diagnostics**: Dumps logs for blog, redis, celery services

### 10. dependency-consistency
- **Tool**: `python scripts/check_dependency_manifest_consistency.py`
- **Purpose**: `requirements.txt`, `pyproject.toml` and the lock/manifest files agree

### 11. release1-package-smoke
- **Tool**: `python -m build --wheel`, installed into an isolated virtualenv
- **Purpose**: Smoke-tests the published wheel — the `devlog` CLI and an app-context operation

### Job Dependency Chain

```
lint-and-type ──> test ──> migration-chain
                      └──> e2e-tests <── docker-build
theme-policy
theme-package-verification
frontend-build
security-audit
dependency-consistency
release1-package-smoke
```

- `lint-and-type` must pass before `test` runs
- `test` must pass before `migration-chain` and `e2e-tests` run
- `docker-build` must pass before `e2e-tests` runs (E2E needs the Docker image)
- The remaining jobs run in parallel with each other

### Schedule

The CI workflow runs on a weekly schedule (Monday 08:00 UTC) in addition to push/PR triggers.

## Test Configuration

From `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=app --cov-report=term-missing"

[tool.coverage.report]
fail_under = 80
```

Additional markers are defined in `pytest.ini`:
```ini
[pytest]
markers =
    e2e: end-to-end browser tests
```

Minimum coverage: 80%

### Running Tests Locally

```bash
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest tests/ --ignore=tests/e2e -v --cov=app --cov-fail-under=80
```

Required environment variables:
- `ADMIN_PASSWORD` - Set to any value for admin tests
- `SECRET_KEY` - Set to any value for session/CSRF tests

## See Also
- [Docker](docker.md) - Docker setup
- [Testing](../testing/test-suite.md) - Test infrastructure
- [Release Validation Skill](../../.skills/release_validation/skill.md) - The local equivalent of the CI gate, and how to diagnose a failing stage
