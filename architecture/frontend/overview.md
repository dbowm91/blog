# Frontend

Frontend assets and templating.

## Overview

| Component | Location | Purpose |
|-----------|----------|---------|
| JavaScript | `app/static/js/` | Vanilla JS modules |
| CSS | `app/static/css/` | Stylesheets |
| Uploads | `app/static/uploads/` | User media |
| Vite Build | `app/static/dist/` | Built assets |
| Templates | `app/templates/` | Jinja2 templates |

## Theme CSS Cache Contract

Theme CSS generation uses an in-process cache (`app/themes/cache.py`) with source-state freshness validation. In multi-worker deployments, each worker maintains its own cache. The cache contract (`docs/themes/cache-contract.md`) defines freshness rules, the invalidation API, and deployment considerations for cache coherence across workers.

## See Also
- [Static Assets](frontend/static-assets.md) - JS/CSS assets
- [Templates](frontend/templates.md) - Jinja2 templates
- [Cache Contract](../../docs/themes/cache-contract.md) - Cache freshness model, invalidation API, multi-worker notes
