# Frontend

Frontend assets and templating.

## Overview

| Component | Location | Purpose |
|-----------|----------|---------|
| JavaScript | `app/static/js/` | Vanilla JS modules |
| CSS | `app/static/css/` | Stylesheets |
| Fonts | `app/static/fonts/` | Self-hosted woff2 families |
| Images | `app/static/img/` | Favicon, default post image, page backdrops |
| Uploads | `app/static/uploads/` | User media, custom fonts and backdrops |
| Vite Build | `app/static/dist/` | Built assets |
| Templates | `app/templates/` | Jinja2 templates |
| Appearance | `app/appearance/` | Font and backdrop registries and service |

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
| Heading anchor | `public/anchor-links.js` | The anchor is a child of the heading, never wrapped; it is transparent until the heading is hovered or the anchor focused |
| Markdown prose | `app/static/css/base.css` | The admin shell does not load `public.css` and the live preview renders `.prose`; `public.css` must not own the prose rules |
| Default profile image | `app/templates/_default_avatar.html` | One macro for every "no profile picture" surface; never fall back to the first letter of the name |
| Route → module set | `main.js` | Match on a path-segment boundary, longest match first |
| Theme colour | the theme runtime | Static CSS consumes tokens; every referenced token is emitted or defined |
| Typeface | the appearance runtime | `--font-sans` and `--font-mono` are emitted by `app/appearance/service.py`; stylesheets never name a family directly |
| Page backdrop | the appearance runtime | `--backdrop-image` and `--backdrop-tint` are emitted per scheme; the SVG supplies shape only, never colour |
| Admin theme preview | `admin/settings.html` (inline script) | Triggers stay with the selects; `min-height` equals `max-height`; clear restores the placeholder; preview CSS stays scoped to `#theme-preview-container` |
| Breakpoint visibility | one stylesheet per breakpoint | Rules that must win must not tie on specificity |
| Stylesheet order | `app/templates/base.html` | `main.js` must not import a stylesheet, or dev and production diverge |

`app/static/AGENTS.override.md` documents each contract with its rationale.
`tests/test_css_contracts.py` and `tests/test_frontend_contracts.py` enforce the
ones that are mechanically checkable.

## See Also
- [Static Assets](frontend/static-assets.md) - JS/CSS assets
- [Templates](frontend/templates.md) - Jinja2 templates
- [Appearance Layer](frontend/appearance.md) - Fonts and page backdrops
- [Cache Contract](../../docs/themes/cache-contract.md) - Cache freshness model, invalidation API, multi-worker notes
