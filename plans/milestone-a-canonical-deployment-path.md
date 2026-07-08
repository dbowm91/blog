# Milestone A Plan: Canonical Single-Server Deployment Path

## Objective

Make DevLog's default production deployment path unambiguous, easy to run, and internally consistent across Docker Compose, README, DEPLOY.md, `.env.example`, CI/e2e smoke coverage, and runtime assumptions.

The current repository has a strong production foundation but exposes several conflicting deployment signals. `docker-compose.yml` puts the `blog` container behind internal `expose: 5000`, publishes nginx on ports 80 and 443, and includes nginx in the `production` profile. The README and deployment guide also describe access at `http://localhost:5000`, while the deployment guide states that TLS should be handled externally. This makes first-run production deployment harder than it needs to be.

This milestone should produce one canonical supported topology for v1 public release.

## Recommended decision

Prefer this v1 topology:

- Single host.
- Docker Compose.
- SQLite WAL using the named `blog_data` volume.
- Local uploads using the named `blog_uploads` volume.
- Redis for production cache/rate limiting and Celery broker.
- One Celery worker container.
- APScheduler disabled by default; if enabled, exactly one app/scheduler owner.
- App reachable only on localhost or an internal Docker network.
- TLS termination handled by the operator's reverse proxy: Caddy, nginx, Traefik, cloud load balancer, or equivalent.

This topology is simpler to support publicly than maintaining a bundled nginx TLS stack. If bundled nginx remains, it must become a first-class supported topology with real TLS instructions, certificate volume handling, and URL/port docs matching nginx, not the app container.

## Files to inspect and modify

Primary files:

- `docker-compose.yml`
- `docker-compose.ci.yml`
- `Dockerfile`
- `.env.example`
- `README.md`
- `DEPLOY.md`
- `.github/workflows/ci.yml`

Secondary files, depending on chosen approach:

- `nginx/nginx.conf`
- `nginx/conf.d/*`
- `scripts/*`
- `tests/e2e/*`

## Implementation approach

### Step 1: Choose and encode the deployment topology

Decide whether nginx is part of the default `production` profile.

Preferred implementation:

- Remove nginx from the default `production` profile, or move it to a separate profile such as `nginx` or `proxy`.
- Publish the app only on localhost in the supported production quick start:

```yaml
services:
  blog:
    ports:
      - "127.0.0.1:5000:5000"
```

- Keep Redis and Celery in the production profile if they are part of the supported v1 topology.
- Keep `ENABLE_SCHEDULER=false` as the safe default.
- Document that Caddy/nginx/Traefik should proxy to `http://127.0.0.1:5000`.

Alternative implementation if bundled nginx stays in production:

- Make the README say the default stack is available at `http://localhost` or `https://localhost`, not `localhost:5000`.
- Provide a complete certificate story.
- Ensure nginx config works without external TLS ambiguity.
- Ensure CI smoke tests reach nginx, not the app port directly.

Do not leave both models half-supported.

### Step 2: Normalize Compose service exposure

If external reverse proxy is selected:

- Change `blog` from `expose` only to a localhost-bound `ports` mapping for normal production profile usage.
- Move nginx out of default startup or mark it optional.
- Ensure `docker-compose.ci.yml` remains minimal and only overrides what CI needs.
- Verify health checks still target the container-local app at `http://localhost:5000/health`.

If bundled nginx remains:

- Keep `blog` internal-only.
- Confirm nginx config proxies correctly to `blog:5000`.
- Ensure nginx has a working default HTTP server for local smoke tests.
- Make the e2e base URL match nginx.

### Step 3: Update README quick start

The README should contain one production path and one development path.

Production quick start should include:

```bash
git clone https://github.com/dbowm91/blog.git /opt/blog
cd /opt/blog
cp .env.example .env
# edit SECRET_KEY and ADMIN_PASSWORD
docker compose --profile production up -d --build
```

Then state the exact access URL that matches Compose.

For the preferred localhost-bound app topology:

- Local machine: `http://127.0.0.1:5000`
- Public production: configure reverse proxy/TLS to forward to `http://127.0.0.1:5000`

Add a short statement that Docker does not automatically issue TLS certificates.

### Step 4: Update DEPLOY.md

DEPLOY.md should start with the canonical path before advanced/manual/systemd options.

Add a section titled approximately `Supported v1 production topology` with:

- Single-server Docker Compose.
- SQLite WAL.
- Local uploads.
- Redis and Celery.
- One scheduler owner.
- External TLS termination.

Then update all references to access URL, nginx, TLS, Compose profiles, and production caveats to match the chosen topology.

### Step 5: Adjust CI/e2e smoke coverage

Update `.github/workflows/ci.yml` and/or `docker-compose.ci.yml` so CI starts the same supported production profile or a clearly named CI variant.

The smoke test should validate:

- Compose starts successfully.
- `/health` returns 200.
- The documented host/port path is reachable.
- Vite manifest exists in the image.
- Redis is healthy.
- Celery starts if included in production profile.

Keep e2e tests pointed at the same external URL a user would hit in the documented quick start.

### Step 6: Add optional reverse proxy examples

For the preferred external TLS topology, include concise examples for Caddy and nginx.

Caddy example:

```caddyfile
blog.example.com {
    reverse_proxy 127.0.0.1:5000
}
```

nginx example:

```nginx
server {
    listen 443 ssl http2;
    server_name blog.example.com;

    ssl_certificate /etc/letsencrypt/live/blog.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/blog.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Do not require users to use nginx unless the project commits to maintaining it as part of the stack.

## Testing requirements

Manual/local validation:

```bash
cp .env.example .env
# fill SECRET_KEY and ADMIN_PASSWORD
docker compose --profile production up -d --build
curl -f http://127.0.0.1:5000/health
curl -I http://127.0.0.1:5000/
docker compose --profile production ps
docker compose --profile production logs --tail=100 blog
docker compose --profile production down -v
```

CI validation should retain:

```bash
docker build -t devlog:ci .
docker run --rm devlog:ci test -f /app/app/static/dist/.vite/manifest.json
```

Add or update Compose smoke validation to match the documented topology.

## Edge cases to handle

- `SESSION_COOKIE_SECURE=true` means login over plain HTTP will not persist sessions. Docs must say local HTTP testing should use `SESSION_COOKIE_SECURE=false`, while production behind HTTPS should keep it true.
- If the app is bound to `127.0.0.1:5000`, public access requires a reverse proxy on the host.
- If nginx is moved to an optional profile, the old nginx docs should not remain in the default quick start.
- If scheduler is enabled with multiple workers, duplicate scheduling risks should remain documented.

## Acceptance criteria

- README and DEPLOY.md describe the same production topology.
- The documented Docker command starts services successfully from a fresh checkout.
- The documented access URL is actually reachable.
- Docker service exposure does not accidentally publish an internal-only app broadly unless that is the intended supported behavior.
- Nginx/TLS documentation is either complete and supported or clearly optional/external.
- CI/e2e smoke coverage exercises the chosen topology.

## Suggested commit scope

Keep this milestone focused. Avoid also changing metrics policy, database support, API auth, or anti-spam behavior in the same patch unless required by deployment smoke tests. Those are covered in later milestone plans.
