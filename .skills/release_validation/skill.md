---
name: release_validation
description: "DevLog release and validation workflow — the full pre-release gate (lint, format, type check, tests, frontend build, Docker build, Compose validation), how to run it, and the host-specific gotchas that make a run fail for reasons unrelated to your change. Use when preparing a release, tagging a version, running the release check, or diagnosing why lint, mypy, pytest, the Vite build, the Docker build or the Compose config check fails."
---

# Release Validation Skill

How to run DevLog's pre-release gate, what each stage actually proves, and the
environment traps that produce failures unrelated to your change.

## The Gate

```bash
./scripts/release_check.sh
```

That runs, in order: dependency install → `ruff check` → `ruff format --check`
→ `mypy` → `pytest` (unit/integration) → `npm ci` + `npm run build` → Docker
image build → `docker compose --profile production config` → the same with
`--profile reverse-proxy`.

For a full release (version bump, wheel, checksums, tag, GitHub release) follow
`RELEASE.md` at the repo root.

## Run It Piece By Piece When Debugging

The script stops at the first failure, which is unhelpful when several stages
are broken at once. Run them individually:

```bash
python3 -m ruff check .
python3 -m ruff format --check .
arch -arm64 python3 -m mypy app/ devlog_cli/
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 \
  python3 -m pytest tests/ --ignore=tests/e2e -q
npm run build
docker build -t devlog:release-check .
docker compose --profile production config > /dev/null
```

Type-check **both** `app/` and `devlog_cli/`. `scripts/release_check.sh` only
passes `app/`, so a `devlog_cli/` type error passes the script but fails CI.

## Always Establish a Baseline First

Do not assume a failure is yours. Before changing anything, record the baseline
on a clean tree and compare:

```bash
git stash push --include-untracked
<run the same command>
git stash pop
diff /tmp/before.txt /tmp/after.txt
```

Capture the **failure set**, not just the count — the same number of failures
can be a different set. This project currently has a known pre-existing
baseline (recorded 2026-10-25):

- `mypy app/ devlog_cli/` — **17 errors** in 7 files (all in `app/themes/translate.py`,
  `app/config_legacy.py`, `app/config/`, `app/cli.py`,
  `app/services/operations/{doctor,database}.py`).
- `pytest tests/ --ignore=tests/e2e` — **69 failures**, concentrated in
  `tests/themes/test_reliability.py`, `tests/test_tasks.py`,
  `tests/test_webhooks.py`, `tests/packaging/`, `tests/filesystem/` and
  `tests/services/test_operations_backup.py`.

A change is clean when the failure set is **identical**, not when the count
matches.

## Host-Specific Gotchas

**Architecture mismatch.** This host is arm64 but the system `python3` is
x86_64. Use `arch -arm64 python3` for mypy. For pytest, the `brotli` C
extension fails to load under the x86_64 interpreter; a shim on `PYTHONPATH`
works around it:

```bash
export PYTHONPATH="/tmp/devlog_review_stubs:$PWD"   # directory containing brotli.py
```

**Restart the server after every Vite build.** `app/vite.py` caches the manifest
process-wide. A rebuild without a restart serves stale asset URLs.

**Do not run the Playwright E2E suite concurrently with the full pytest
suite.** They share the development database and corrupt each other's DDL.
Browser-level tests belong under `tests/e2e/` on the e2e app's own
`blog_e2e` database.

**Disk space.** The drive runs near capacity. A Docker image build or a large
pytest run can fail on a full disk, which looks like an unrelated error.

**`.env` is required and gitignored.** `config.toml` is gitignored too; only
`config.toml.example` is committed. `python-dotenv` auto-loads `.env`, so
exporting the variables manually is optional but harmless.

**Test credentials.** Every test reads `os.environ["ADMIN_PASSWORD"]`. The
standard values are `test-password-123` and
`test-secret-key-test-secret-key-1234`.

## What Each Stage Actually Proves

| Stage | Proves | Does not prove |
|---|---|---|
| `ruff check` | No lint errors | Nothing about types |
| `ruff format --check` | Formatting matches the project style | Nothing about correctness |
| `mypy` | The declared types line up | Runtime behaviour |
| `pytest` | Unit and integration behaviour | E2E, Docker, deployment |
| `npm run build` | The bundle compiles and the manifest is written | That the manifest is *served* — restart the server |
| `docker build` | The image builds, including the `frontend-builder` stage | That the compose stack runs |
| `compose config` | The compose file is valid for that profile | That the services start |

## CI Jobs

`.github/workflows/ci.yml` runs **11 jobs**:

`lint-and-type`, `test`, `theme-policy`, `migration-chain`,
`theme-package-verification`, `frontend-build`, `security-audit`,
`docker-build`, `e2e-tests`, `dependency-consistency`, `release1-package-smoke`.

Two of them are not covered by `release_check.sh`:

- **`theme-policy`** — the accessibility gate. Equivalent to
  `devlog themes accessibility --strict` plus the policy check in
  `scripts/verify_theme_package.py`.
- **`migration-chain`** — runs the Alembic migrations in a real
  `Operations` context, both up and down. A migration that imports models at
  module scope will break here.

`dependency-consistency` runs
`python scripts/check_dependency_manifest_consistency.py`.

## Frontend Build

```bash
npm ci
npm run build
```

Output lands in `app/static/dist/` with the manifest at
`app/static/dist/.vite/manifest.json`. Without it, templates fall back to
unbundled source paths and production code-splitting silently does not work.
Docker builds handle this in the `frontend-builder` stage.

## Release Artifacts

```bash
python -m build --wheel
python scripts/check_release_artifacts.py --directory dist/
python scripts/generate_checksums.py --directory dist/
python scripts/check_release_artifacts.py --directory dist/ --checksums dist/checksums.txt
```

## Related

- `RELEASE.md` — the release checklist and version-bump steps
- `CONTRIBUTING.md` — contribution and commit conventions
- `architecture/testing/test-suite.md` — the test suite layout
- `architecture/deployment/cicd.md` — the CI pipelines in detail
