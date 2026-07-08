# Release Checklist

Use this checklist before tagging a new release.

## Pre-Release

- [ ] All tests pass: `ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python -m pytest tests/ -v`
- [ ] Lint passes: `ruff check .`
- [ ] Format check passes: `ruff format --check .`
- [ ] Type check passes: `mypy app/`
- [ ] Frontend builds: `npm run build`
- [ ] No secrets in tracked files: `git diff --name-only HEAD~5..HEAD | xargs grep -l "SECRET_KEY\|ADMIN_PASSWORD" || true`
- [ ] Security audit passes: `pip-audit -r requirements.txt --fail-on=all`
- [ ] `config.toml` is NOT tracked (only `config.toml.example` is committed)
- [ ] CHANGELOG.md updated with release version and date
- [ ] `HEALTH_CHECK_SECRET` and `METRICS_SECRET` are set in production environment

## Version Bump

- [ ] Update `version` in `pyproject.toml`
- [ ] Update `CHANGELOG.md`: move `[Unreleased]` content under `[X.Y.Z]` with date
- [ ] Create git tag: `git tag -a vX.Y.Z -m "Release X.Y.Z"`

## Post-Release

- [ ] Push tag: `git push origin vX.Y.Z`
- [ ] Create GitHub Release from tag
- [ ] Verify Docker build: `docker compose --profile production build`
- [ ] Deploy to staging/production
- [ ] Smoke test: homepage loads, login works, posts render, feeds accessible
