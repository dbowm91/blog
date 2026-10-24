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

## Cross-Layer Contracts

The frontend is a set of layers that each look correct in isolation and disagree at
the seams. Those seams are where the defects live, so each has a named owner:

| Value | Owner | Consumers must |
|---|---|---|
| Post image URL | `post_image_url` filter (`app/filters.py`) | Use the URL directly; never re-wrap it with `url_for('static', …)` |
| Responsive `srcset` | `post_image_srcset` filter | Guard the attribute — the filter returns `None` when no variants exist |
| Image visibility | `shared/lazy-load.js` | Any rule that hides an element must have a guaranteed restoration path |
| Lightbox visibility | the `hidden` class | `hidden` is visibility; `open` is animation state |
| CSRF header name | `app/csrf.py` (`CSRF_HEADER_NAME`) | Read it from `data-csrf-header` or `csrfHeaders()`; never hard-code it |
| Heading IDs | `shared/heading-slug.js` | One generator only |
| Route → module set | `main.js` | Match on a path-segment boundary, longest match first |
| Theme colour | the theme runtime | Static CSS consumes tokens; every referenced token is emitted or defined |
| Admin theme preview | `admin/settings.html` (inline script) | Triggers stay with the selects; `min-height` equals `max-height`; clear restores the placeholder; preview CSS stays scoped to `#theme-preview-container` |
| Breakpoint visibility | one stylesheet per breakpoint | Rules that must win must not tie on specificity |
| Stylesheet order | `app/templates/base.html` | `main.js` must not import a stylesheet, or dev and production diverge |

`app/static/AGENTS.override.md` documents each contract with its rationale.
`tests/test_css_contracts.py` and `tests/test_frontend_contracts.py` enforce the
ones that are mechanically checkable.

## See Also
- [Static Assets](frontend/static-assets.md) - JS/CSS assets
- [Templates](frontend/templates.md) - Jinja2 templates
- [Cache Contract](../../docs/themes/cache-contract.md) - Cache freshness model, invalidation API, multi-worker notes
