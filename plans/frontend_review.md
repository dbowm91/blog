# Frontend Module Architecture Review

**Reviewed:** May 29, 2026
**Architecture Docs:** overview.md, templates.md, static-assets.md
**Source Files:** app/filters.py, app/context_processors.py, app/vite.py, app/templates/, app/static/

## Findings

### Verified Claims (Correct)

- **filters.md filters list**: All six filter names, descriptions, and deprecation status match `app/filters.py:12-88`
- **Context processors**: All five processors (`inject_csrf`, `inject_config`, `inject_theme`, `inject_footer_data`, `inject_show_footer_posts`) and their returned variables match `app/context_processors.py:126-183`
- **Cache invalidation functions**: `invalidate_settings_cache()` (line 30-32) and `invalidate_footer_cache()` (line 35-37) confirmed correct
- **Template directory structure**: All files listed in templates.md exist in `app/templates/`
- **Admin template files**: All 31 admin templates exist
- **JS directory structure**: All listed files in `app/static/js/` exist (admin/, public/, shared/, lib/)
- **CSS file list**: All listed CSS files exist in `app/static/css/`
- **Font files**: Inter (300-700) and JetBrains Mono (400, 500) woff2 files confirmed
- **Route-based code splitting**: `ROUTE_MODULES` and `getModulesForPath()` in `main.js:30-83` match documentation
- **Vite config**: Entry point, output, manualChunks, esbuildOptions, dev server port/proxy all match `vite.config.js`
- **Chunk split**: `vendor` (Prism), `admin` (editor.js), `public` (search.js) match `vite.config.js:15-24`
- **Prism lazy loading**: `loadPrismIfNeeded()` at `main.js:97-112` confirmed
- **Module initialization pattern**: `loadModule()` at `main.js:85-96` calls `module.default()` if it exists
- **Admin body class**: `admin-body` class referenced in `app/static/css/layout.css:51`

### Discrepancies (Doc vs Code)

1. **templates.md:66-72 — Template inheritance diagram is inaccurate**
   Admin templates extend `admin/base.html` (a separate base template with its own `<html>/<head>/<body>`), NOT the root `base.html`. Additionally, login pages (`login.html`, `login_2fa.html`, `reset-password.html`, `forgot-password.html`) extend `admin/login_base.html` (a third base template), and email templates extend `email/base_email.html`. The inheritance tree should show four separate roots, not two.

2. **static-assets.md:175 — Critical CSS line reference wrong**
   Doc says: "Loaded in `base.html:22`"
   Actual: `base.html:25` (`<link rel="stylesheet" href="{{ vite_asset('css/critical.css') }}" media="screen">`)

3. **static-assets.md:182 — Font preload line reference wrong**
   Doc says: "Preloaded in `base.html:37-38`"
   Actual: `base.html:40-41`

4. **static-assets.md:186 — Syntax theme CSS line reference wrong**
   Doc says: "loaded dynamically in `base.html:28`"
   Actual: `base.html:31` (loaded via `media="print" onload="this.media='all'"`, not dynamically)

5. **static-assets.md:199 — `vite_asset()` function line reference wrong**
   Doc says: "`app/vite.py:47`"
   Actual: `app/vite.py:48`

6. **static-assets.md:199 — `init_vite()` line reference wrong**
   Doc says: "`app/vite.py:80-82`"
   Actual: `app/vite.py:81-83`

7. **static-assets.md:116-121 — Lazy load description misleading**
   Doc says tier 1: "use native `loading="lazy"` attribute"
   Actual: The code returns early (does nothing) — the browser handles `loading="lazy"` natively. The JS doesn't "use" the attribute; it defers to the browser. The HTML templates already include `loading="lazy"` on `<img>` tags.

8. **static-assets.md:166 — Dark mode default description misleading**
   Doc says: "Dark mode is the default (no `data-theme` attribute = dark)"
   Actual: Default follows OS preference via `prefers-color-scheme: dark` (`dark-mode.js:13-14`). If OS is light mode, `data-theme="light"` is set immediately. The attribute-removal logic means "no attribute = dark" only if the user has toggled to dark, not as an unconditional default.

### Missing Documentation

1. **`admin/login_base.html` — Third base template not documented**
   `app/templates/admin/login_base.html` is a standalone base template for auth pages. Used by `login.html`, `login_2fa.html`, `reset-password.html`, `forgot-password.html`. The templates.md inheritance section only mentions `base.html` and `admin/*.html`.

2. **`email/base_email.html` — Email base template not documented**
   `app/templates/email/base_email.html` is a base template for email templates (`confirm.html`, `newsletter.html`, `password_reset.html`). Not mentioned in templates.md.

3. **`post_image_srcset` filter — Missing implementation details**
   Doc says only "Generate srcset for responsive images." Missing: variant widths (400, 800, 1200), CDN_URL handling, and the `_post_srcset_cache_` cache key pattern (`app/filters.py:57-76`).

4. **`img-skeleton` shimmer animation not documented**
   `app/static/css/public.css:1125-1138` defines a shimmer loading animation for `.img-skeleton` images. The static-assets.md "Lazy Image Loading" section only mentions opacity transitions, not the shimmer skeleton effect.

5. **`overview.md` — Missing `node_modules/` and `dist/` from structure**
   `app/static/node_modules/` exists but is not listed. `app/static/dist/` IS listed, which is correct.

### Potential Bugs / Concerns

1. **`base.html:19,24` — Duplicate Atom feed `<link>` tags**
   Line 19 outputs an Atom feed link inside `{% block feed_links %}`, and line 24 outputs an identical hardcoded Atom feed link outside the block. Every page rendered with `base.html` will have two identical feed links in the `<head>`. This is a template bug, not a documentation issue, but was discovered during review.

### Improvement Suggestions

1. **static-assets.md** should clarify that `base.html:25` loads critical CSS via `media="screen"` while other stylesheets use `media="print" onload="this.media='all'"` for deferred loading (the deferred pattern is mentioned but the line reference is wrong).

2. **templates.md** should document the four base templates (`base.html`, `admin/base.html`, `admin/login_base.html`, `email/base_email.html`) and their respective inheritance trees.

3. **static-assets.md** lazy loading section should distinguish between "browser handles natively" (tier 1) vs "JS polyfill" (tiers 2-3), rather than implying JS does something for tier 1.

## Action Items

| # | Priority | Description | Docs Affected |
|---|----------|-------------|---------------|
| 1 | high | Fix template inheritance diagram to show four base templates (`base.html`, `admin/base.html`, `admin/login_base.html`, `email/base_email.html`) and their children | templates.md |
| 2 | high | Fix line number references: `base.html:25` (critical CSS), `base.html:40-41` (font preload), `base.html:31` (syntax theme), `app/vite.py:48` (`vite_asset`), `app/vite.py:81-83` (`init_vite`) | static-assets.md |
| 3 | med | Rewrite lazy loading tier 1 description to clarify JS defers to native browser handling rather than "using" the attribute | static-assets.md |
| 4 | med | Fix dark mode default description to note it follows OS preference, not unconditional dark | static-assets.md |
| 5 | med | Add `post_image_srcset` filter implementation details (variant widths, CDN_URL handling, cache key) | templates.md |
| 6 | low | Document `img-skeleton` shimmer animation in the lazy loading section | static-assets.md |
| 7 | low | Add `admin/login_base.html` and `email/base_email.html` to template directory structure listing | templates.md |
| 8 | low | Fix duplicate Atom feed link in `base.html:24` (template bug) | N/A (code fix) |
