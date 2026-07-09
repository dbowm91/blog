# Nginx Configuration (Optional)

This directory contains an **optional** nginx reverse proxy configuration for DevLog. It is part of the `reverse-proxy` Compose profile and is **not** part of the core production stack.

## When to Use

- You want to manage nginx inside Docker Compose instead of on the host
- You have a valid TLS certificate ready to mount

For most single-host deployments, a host-level reverse proxy (Caddy, nginx, Traefik) is simpler and recommended. See [DEPLOY.md § Reverse Proxy Setup](../DEPLOY.md#9-reverse-proxy-setup).

## Certificate Requirements

The nginx configuration expects TLS certificates at:

```
/etc/letsencrypt/live/blog.example.com/fullchain.pem
/etc/letsencrypt/live/blog.example.com/privkey.pem
```

You must mount valid certificates before starting the nginx service. The configuration will fail without them.

## Usage

```bash
# Start with both production and reverse-proxy profiles
docker compose --profile production --profile reverse-proxy up -d --build

# Validate nginx config syntax (without starting)
docker run --rm -v $(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
  -v $(pwd)/nginx/conf.d:/etc/nginx/conf.d:ro \
  nginx:alpine nginx -t
```

## What It Provides

- TLS termination (requires certificates)
- HTTP-to-HTTPS redirect
- Rate limiting (login: 5 req/min, admin: 20 req/min)
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- Static file serving
- Gzip compression

## What It Does NOT Provide

- Automatic certificate management (use Certbot or similar)
- HTTP-to-HTTPS redirect without valid certificates
- Any security benefit without proper certificate configuration
