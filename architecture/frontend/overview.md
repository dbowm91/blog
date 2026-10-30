# Frontend

Frontend assets and templating.

## Overview

| Component | Location | Purpose |
|-----------|----------|---------|
| JavaScript | `app/static/js/` | Vanilla JS modules |
| CSS | `app/static/css/` | Stylesheets; `projects.css` owns the project directory and landing layouts |
| Fonts | `app/static/fonts/` | Self-hosted woff2 families |
| Images | `app/static/img/` | Favicon, the post placeholder mark and its social raster, page backdrops |
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
| Public navigation data | `app/services/navigation.py` | Templates consume the unified projection; they do not select page/project links themselves |
| Project theme overrides | `app/services/projects.py` | Theme variables are scoped to the project container; global theme state is unchanged |
| Post image URL | `post_image_url` filter (`app/filters.py`) | Use the URL directly; never re-wrap it with `url_for('static', …)` |
| Responsive `srcset` | `post_image_srcset` filter | Guard the attribute — the filter returns `None` when no variants exist |
| Image visibility | `shared/lazy-load.js` | Any rule that hides an element must have a guaranteed restoration path |
| Lightbox visibility | the `hidden` class | `hidden` is visibility; `open` is animation state |
| CSRF header name | `app/csrf.py` (`CSRF_HEADER_NAME`) | Read it from `data-csrf-header` or `csrfHeaders()`; never hard-code it |
| Heading IDs | `shared/heading-slug.js` | One generator only |
| Heading anchor | `public/anchor-links.js` | The anchor is a child of the heading, never wrapped; it is transparent until the heading is hovered or the anchor focused |
| Markdown prose | `app/static/css/base.css` | The admin shell does not load `public.css` and the live preview renders `.prose`; `public.css` must not own the prose rules |
| Reading measure | `app/static/css/base.css` | `max-width: 34em` on `.prose`, in `em` so it scales with the prose font size; `public.css` sets no width on `.post-body` |
| Post placeholder mark | `app/static/css/public.css` | The `.img-placeholder` rule applies the SVG as a mask and takes the ink from `--text-dim`; the mark is never loaded as an image |
| Default profile image | `app/templates/_default_avatar.html` | One macro for every "no profile picture" surface; never fall back to the first letter of the name |
| Post list grid | `app/static/css/public.css` (`.posts-list`), mirrored in `critical.css` | Two tracks from 1024px; the tracks are `minmax(0, 1fr)` so a long title shrinks its own column; `critical.css` paints the same grid because it is the first paint |
| Card tag row | `post_tag_row` macro (`app/templates/macros.html`) | One owner for the cap: at most four tags, then a `+N` label with an accessible name; a card never holds the only copy of a tag — the post footer carries the full list |
| Structural voice | `app/static/css/public.css` (`.post-toc-title`, `.share-label`) and `app/static/css/layout.css` (`.sidebar-title`) | One shared treatment — mono face, uppercase, caption role; each label is declared in exactly one sheet, and the table-of-contents entries keep the body face and read as links |
| Share bar position | `app/templates/_post_content.html` | The bar follows `.post-body` and precedes `.author-card`; its markup and data attributes are unchanged, so the share JavaScript is unaffected |
| Route → module set | `main.js` | Match on a path-segment boundary, longest match first |
| Theme colour | the theme runtime | Static CSS consumes tokens; every referenced token is emitted or defined |
| Typeface | the appearance runtime | `--font-sans` and `--font-mono` are emitted by `app/appearance/service.py`; stylesheets never name a family directly |
| Page backdrop | the appearance runtime | `--backdrop-image` and `--backdrop-tint` are emitted per scheme; the SVG supplies shape only, never colour |
| Admin theme preview | `admin/settings.html` (inline script) | Triggers stay with the selects; `min-height` equals `max-height`; clear restores the placeholder; preview CSS stays scoped to `#theme-preview-container` |
| AI post suggestions | `admin/editor.html` + `admin/editor.js` | Controls render only when server config has a usable key; only explicit clicks send current unsaved title/body. Show plain-text suggestions, require a separate Apply action, guard against stale source/destination edits, and persist only through normal Save |
| Markdown media safety | `app/markdown_renderer.py` + `app/markdown_config.py` | One sanitizer owns public, preview, and feed markup. Uploaded videos are limited to local/configured storage URLs; iframe embeds are restricted to the YouTube-nocookie embed path and Flask owns the single CSP policy. Attachment links use the forced-download route |
| Post editor drafts and dirty state | `admin/editor.js` | Title/body/summary/tags share local draft save/restore and unsaved-change detection; tag updates dispatch input/change like the other fields |
| Editor Media and Attachment pickers | `admin/media-picker.js` + `admin/editor.js` | Shared by post/page Markdown editors; use the author-protected categorized catalog/upload API and shared CSRF helper. Media inserts inline images or controlled video markup; Attachment always inserts a forced-download link. Insertions dispatch input and structural history events and preserve the editor selection/focus contract |
| Breakpoint visibility | one stylesheet per breakpoint | A media query adds no specificity: the sheet that owns an element's base rule owns its breakpoint override too |
| Stylesheet order | `app/templates/base.html` | `main.js` must not import a stylesheet, or dev and production diverge |
| Project landing column | `app/static/css/projects.css` | The landing page is one column; the breadcrumb, the header, the prose and the gallery share its left edge. `projects.css` overrides the centred prose measure for `.project-body` only, so the title and the body line up |

## Project Landing Layouts

`app/templates/projects/_layout_<style>.html` holds one layout each, and
`projects/landing.html` picks the one named by the project's `landing_style`.
The style is a layout identifier, never a theme identifier.

| Layout | Shape | Notes |
|---|---|---|
| `product` | Hero band, feature grid, centred prose, gallery, closing call to action | The product-page layout; the hero image renders in a window frame |
| `showcase` | Header, full-width framed hero, feature grid, centred prose, gallery, closing call to action | Leads with the visual |
| `documentation` | Header, body in the main column, resources in a sticky rail | The rail reuses the `.project-docs-main` / `.project-docs-rail` grid the documentation pages use, so the body never lands in the rail column |
| `minimal` | Header, prose, gallery | A document column; the prose is left-aligned with the title |
| `terminal` | Header, body inside a terminal window, gallery | The body fills the window rather than holding the prose measure |

Every layout renders the project's feature grid, and every layout renders a
configured hero image. A layout never drops a field the administrator set.

`app/static/AGENTS.override.md` documents each contract with its rationale.
`tests/test_css_contracts.py` and `tests/test_frontend_contracts.py` enforce the
ones that are mechanically checkable.

## See Also
- [Static Assets](static-assets.md) - JS/CSS assets
- [Templates](templates.md) - Jinja2 templates
- [Appearance Layer](appearance.md) - Fonts and page backdrops
- [Cache Contract](../../docs/themes/cache-contract.md) - Cache freshness model, invalidation API, multi-worker notes
