#!/usr/bin/env bash
set -euo pipefail

# Release validation script for DevLog.
# Runs lint, type check, tests, frontend build, Docker build, and Compose config validation.

echo "=== DevLog Release Check ==="

echo ""
echo "--- Installing dev dependencies ---"
python -m pip install -q -r requirements-dev.txt

echo ""
echo "--- Ruff lint ---"
ruff check .

echo ""
echo "--- Ruff format check ---"
ruff format --check .

echo ""
echo "--- Mypy type check ---"
mypy app/ devlog_cli/

echo ""
echo "--- Pytest (unit/integration) ---"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-test-password-123}" \
SECRET_KEY="${SECRET_KEY:-test-secret-key-test-secret-key-1234}" \
  python -m pytest tests/ --ignore=tests/e2e -v --cov=app --cov-fail-under=80

echo ""
echo "--- Frontend build ---"
npm ci
npm run build

echo ""
echo "--- Docker build ---"
docker build -t devlog:release-check .

echo ""
echo "--- Compose config (production profile) ---"
docker compose --profile production config > /dev/null

echo ""
echo "--- Compose config (production + reverse-proxy profiles) ---"
docker compose --profile production --profile reverse-proxy config > /dev/null

echo ""
echo "=== All checks passed ==="
