# Phase 5: Docker, Frontend Assets, and Runtime Image Fidelity

## Objective

Make the production Docker image match the documented production asset model. A container built from the repository should contain all runtime dependencies and frontend assets needed to serve the app correctly without relying on an untracked local build artifact.

## Problems to Address

The project has a Vite build pipeline and CI runs `npm ci` plus `npm run build`. The app has Vite manifest integration for content-hashed assets. The agent guidance says production requires the Vite build and manifest. The Dockerfile, however, installs only Python dependencies and does not run the frontend build. Because `app/static/dist/` is ignored, the Docker build context will not include a locally built manifest unless the user changes ignore behavior or builds assets out-of-band.

This creates a mismatch among CI, docs, Docker, and runtime asset behavior.

## Scope

This phase covers Dockerfile build stages, Compose image behavior, Vite manifest handling, asset documentation, and smoke tests. It does not redesign the frontend stack.

## Target Design

Prefer a multi-stage Dockerfile:

1. Node builder stage runs `npm ci` and `npm run build`.
2. Python builder stage installs Python dependencies into a venv.
3. Runtime stage copies the Python venv, application code, and built `app/static/dist` assets.
4. Runtime remains slim and non-root.

The image should be self-contained for production. A user should not need to run `npm run build` on the host before `docker build .`.

## Implementation Steps

1. Add a Node asset builder stage.

   Example structure:

   ```dockerfile
   FROM node:20-alpine AS frontend-builder
   WORKDIR /app
   COPY package.json package-lock.json ./
   RUN npm ci
   COPY app/static ./app/static
   COPY vite.config.js ./
   RUN npm run build
   ```

   Adjust paths for the actual Vite root. Confirm that build output lands at `app/static/dist`.

2. Preserve Python dependency builder stage.

   Keep the existing Python venv builder. Consider installing with constraints if phase 2 adds them.

3. Copy frontend artifacts into runtime.

   After copying the app source, copy from `frontend-builder`:

   ```dockerfile
   COPY --from=frontend-builder --chown=blog:blog /app/app/static/dist /app/app/static/dist
   ```

   Ensure ownership is correct for the non-root `blog` user.

4. Verify `.dockerignore` behavior.

   If no `.dockerignore` exists, add one. It should exclude local virtualenvs, node_modules, instance data, logs, uploads, backups, test caches, and local env files. Do not exclude files needed for Docker build such as `package-lock.json`, `vite.config.js`, templates, static source files, migrations, or docs needed by runtime.

5. Decide whether Playwright dependencies belong in runtime.

   `requirements.txt` currently includes Playwright and pytest-related packages, which are test/development dependencies. For a lean production image, move test-only dependencies to `requirements-dev.txt`. Be careful: if any runtime feature actually needs Playwright, document why. Otherwise, production image should not include E2E tooling.

6. Revisit runtime worker count.

   Dockerfile currently starts Granian with four workers. After phase 4, ensure this default does not accidentally start scheduler instances. If SQLite remains the default database, consider whether four web workers is appropriate for single-writer SQLite and background task design. Document the tradeoff if kept.

7. Make health check match Compose topology.

   The Dockerfile checks `http://localhost:5000/health`. Compose also checks the same from inside the container. Confirm `/health` does not require a secret for the basic liveness path. Detailed health can remain secret-protected.

8. Add a Docker build smoke test.

   CI should verify:

   - `docker build .` succeeds.
   - The built image contains `app/static/dist/.vite/manifest.json` if manifest is required.
   - A container can start with minimal valid env and answer `/health`.

9. Update docs.

   README and DEPLOY.md should say Docker builds frontend assets automatically. Manual non-Docker deployments should still instruct `npm ci && npm run build` before production service restart.

## Tests to Add or Update

Add CI steps or scripts for:

- Inspecting built image asset manifest.
- Starting the image with minimal env and checking `/health`.
- Confirming missing Vite manifest behavior only occurs in development or documented fallback mode.

If adding `.dockerignore`, verify no required files are excluded by running Docker build from a clean checkout.

## Verification Commands

```bash
npm ci
npm run build
docker build -t devlog:prod-smoke .
docker run --rm devlog:prod-smoke test -f /app/app/static/dist/.vite/manifest.json
```

Container smoke:

```bash
docker run --rm -p 5000:5000 \
  -e SECRET_KEY=test-secret-key-test-secret-key-1234 \
  -e ADMIN_PASSWORD=test-password-123 \
  -e SESSION_COOKIE_SECURE=false \
  devlog:prod-smoke

curl -f http://localhost:5000/health
```

Compose smoke:

```bash
cp .env.example .env
# Fill required secrets.
docker compose --profile production up -d --build
docker compose ps
docker compose logs blog --tail=100
```

## Acceptance Criteria

A fresh Docker build includes production frontend assets. Docker startup does not depend on host-built ignored files. CI catches missing asset manifest or broken frontend build. Runtime image excludes avoidable dev/test dependencies unless explicitly justified. Docker documentation matches actual behavior.

## Risks

Adding Node to Docker build can increase build time. Use Docker layer caching by copying package files before app source. Moving dependencies from runtime to dev requirements can break hidden runtime imports; use tests and import scans before removing anything from production requirements.
