# Frontend Module Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** overview.md, templates.md, static-assets.md
**Source Files:** app/templates/, app/static/, app/filters.py, app/vite.py, app/context_processors.py

## Findings

### Verified Claims (Correct)

- **Filter names and behaviors** (templates.md:86-92): All six filters (`markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`) match actual code in `app/filters.py`.
- **`post_image_srcset` width variants** (templates.md:91): Checks for 400, 800, and 1200 widths — confirmed at `app/filters.py:68`.
- **`post_image_avif_url_stub` is DEPRECATED** (templates.md:92): Always returns `None` — confirmed at `app/filters.py:78-88`.
- **Context processor variable names** (templates.md:99-100): `site_title` (not `site_name`) and `site_description` (not `site_tagline`) — confirmed at `app/context_processors.py:144-145`. No templates use `site_name` or `site_tagline`.
- **All five context processors** (templates.md:96-105): `inject_csrf`, `inject_config`, `inject_theme`, `inject_footer_data`, `inject_show_footer_posts` — all confirmed in `app/context_processors.py:126-183`.
- **Cache invalidation functions** (templates.md:110-111): `invalidate_settings_cache()` at lines 30-32, `invalidate_footer_cache()` at lines 35-37 — confirmed.
- **`inject_show_footer_posts` hides footer on search/tag pages** (templates.md:105): Confirmed at `app/context_processors.py:182-183`.
- **critical.css loading** (static-assets.md:182): Loaded in `base.html:24` with `media="screen"` — confirmed at line 24.
- **Deferred CSS loading pattern** (static-assets.md:182): Other stylesheets use `media="print" onload="this.media='all'"` — confirmed at `base.html:25-30`.
- **Lazy image CSS pattern** (static-assets.md:109-112): `.js img[loading="lazy"]` with opacity 0, `.loaded` transitions to opacity 1 — confirmed at `public.css:1114-1123`.
- **Image skeleton shimmer** (static-assets.md:116-119): `.img-skeleton` with linear-gradient and shimmer keyframe — confirmed at `public.css:1125-1138`.
- **`main.js` adds `.js` class** (static-assets.md:112): `document.documentElement.classList.add('js')` at line 3 — confirmed.
- **Lazy-load.js three-tier fallback** (static-assets.md:123-127): Native lazy loading check, IntersectionObserver with `rootMargin: '200px 0px'`, immediate fallback — all confirmed at `app/static/js/shared/lazy-load.js:1-32`.
- **Dark mode behavior** (static-assets.md:172-178): OS preference default, localStorage persistence, `data-theme="light"` toggling, OS change listener — all confirmed at `app/static/js/shared/dark-mode.js:12-49`.
- **Admin body class detection** (static-assets.md:131): `admin/base.html:28` and `admin/login_base.html:27` both use `<body class="admin-body">` — confirmed.
- **Route-based code splitting** (static-assets.md:62-103): `ROUTE_MODULES` and `getModulesForPath()` match actual code at `main.js:30-83`.
- **Module loader pattern** (static-assets.md:50-51): `loadModule` checks `module.default` and calls it — confirmed at `main.js:85-96`.
- **Lazy-load.js rootMargin** (static-assets.md:126): `rootMargin: '200px 0px'` — confirmed at `lazy-load.js:29`.
- **`vite_asset()` function** (static-assets.md:208): Registered as Jinja2 global via `init_vite()` at `app/vite.py:81-83` — confirmed.
- **`vite_asset()` behavior** (static-assets.md:210-213): JS lookup from manifest, CSS hash as query string, CDN_URL prefix — confirmed at `app/vite.py:48-78`.
- **Manual chunks split** (static-assets.md:217-220): `vendor` (prism), `admin` (editor.js), `public` (search.js) — confirmed at `vite.config.js:15-25`.
- **Font self-hosting** (static-assets.md:186-189): Inter (300-700) and JetBrains Mono (400, 500) in `app/static/fonts/` — confirmed by directory listing.
- **Font preloading** (static-assets.md:189): `base.html:39-40` preloads inter-400 and jetbrains-mono-400 with `crossorigin` — confirmed.
- **Prism themes** (static-assets.md:169): Six Prism CSS themes present in `app/static/css/` — confirmed (prism.css, prism-dark.css, prism-coy.css, prism-funky.css, prism-okaidia.css, prism-tomorrow.css).
- **Syntax theme via data attribute** (static-assets.md:193): `data-prism-css-url` on `<html>` element set via `vite_asset()` — confirmed at `base.html:2` and `admin/base.html:2`.
- **Prism lazy loading for public pages** (static-assets.md:193): `loadPrismIfNeeded()` checks for `pre[class*="language-"]` — confirmed at `main.js:97-112`.
- **Template directory structure** (templates.md:7-63): All listed files and directories match actual filesystem.
- **Directory overview** (overview.md:7-12): All five components and locations are accurate.
- **admin/login_base.html uses vite_asset()** (AGENTS.md): Confirmed at `login_base.html:7-13`.
- **`vite.config.js` dev server** (static-assets.md:202): Port 3000 with proxy to Flask on port 5000 — confirmed at `vite.config.js:30-34`.

### Discrepancies (Doc vs Code)

- **CRITICAL — templates.md:68-81: Template inheritance diagram is wrong.**
  - Doc claims `admin/base.html` extends `base.html`. **Actual:** `admin/base.html` is a standalone template — it starts with `<!DOCTYPE html>` (line 1) and has its own complete `<head>` with all CSS links. It does NOT contain `{% extends %}`.
  - Doc claims `admin/login_base.html` extends `base.html`. **Actual:** `admin/login_base.html` is also standalone — starts with `<!DOCTYPE html>` (line 1), has its own `<head>`, no `{% extends %}`.
  - Both admin base templates duplicate the full HTML boilerplate (doctype, head, meta, CSS, theme vars, footer, scripts) instead of inheriting from `base.html`.

- **templates.md:62-63: `public/*.html (extends base.html)` is misleading.**
  - The only file in `public/` is `comments.html`, which defines a Jinja `{% macro render_comments() %}` — it is NOT a page template that extends `base.html`. The inheritance diagram implies `public/comments.html` extends `base.html`, which is false.

- **static-assets.md:193: Prism lazy-loading claim is only half correct.**
  - Doc says "Prism.js itself is lazy-loaded by main.js:97-112 only when code blocks are present."
  - **For public pages:** Correct — `base.html` has no Prism `<script>` tags; Prism is loaded dynamically by `main.js:loadPrismIfNeeded()`.
  - **For admin pages:** Wrong — `admin/base.html:162-163` loads Prism eagerly via `<script defer>` tags (`prism.min.js` and `prism-languages.js`). Then `main.js:loadPrismIfNeeded()` also runs on DOMContentLoaded, potentially attempting to load Prism again dynamically if code blocks exist on the page.

- **static-assets.md:135: vite.config.js JSX line reference is wrong.**
  - Doc says "vite.config.js:31-39" for JSX support.
  - **Actual:** The `optimizeDeps.esbuildOptions` block starts at line 36, and `.jsx` loader is at line 40. Lines 31-35 are the `server` block.

- **static-assets.md:137-146: vite.config.js code example is incomplete.**
  - Doc shows only `.js` and `.jsx` loaders.
  - **Actual:** `vite.config.js:41` also has `'.svg': 'text'` loader, which is undocumented.

- **static-assets.md:173: dark-mode.js line reference is slightly off.**
  - Doc says "dark-mode.js:13-14" for the `prefers-color-scheme` check.
  - **Actual:** `const prefersDark` is at line 13, `const isDark` is at line 14. The description spans lines 12-14 (including `localStorage.getItem` at line 12).

- **static-assets.md:148-157: Admin JS and Public JS sections are vague/incorrect.**
  - Doc says "Admin JS: Dashboard functionality, Post editor enhancements, Media management, Settings forms." — These are vague descriptions of functionality, not actual module names.
  - Doc says "Public JS: Comments submission, Newsletter subscription, Search functionality." — The actual `public/` JS files are: `anchor-links.js`, `code-copy.js`, `lightbox.js`, `media-copy.js`, `search.js`, `share.js`, `toc.js`. There is no `comments.js` or `newsletter.js` file. Comments and newsletter are handled server-side.

- **admin/base.html:9: Prism CSS is hardcoded to okaidia.**
  - `admin/base.html:9`: `<link rel="stylesheet" href="{{ vite_asset('css/prism-okaidia.css') }}">` — hardcoded.
  - **In contrast**, `base.html:30` uses `{{ vite_asset('css/' + syntax_theme + '.css') }}` — respects the user's `syntax_theme` setting.
  - Admin pages always use okaidia theme regardless of the SiteSettings `syntax_theme` configuration.

- **templates.md:110-111: Cache invalidation line references.**
  - Doc says `invalidate_settings_cache()` is at "line 30-32" and `invalidate_footer_cache()` is at "line 35-37". These are correct as of the current file. However, these are function definition lines, not the `__all__` export. The `__all__` declaration is at line 3. Minor clarification needed.

### Missing Documentation

- **marked.min.js loaded outside Vite pipeline.** Both `base.html:150` and `admin/base.html:164` load `marked.min.js` via `url_for('static', filename='js/lib/marked.min.js')` — NOT via `vite_asset()`. This means no content hashing, no CDN support, and no cache busting. This pattern is undocumented in any architecture doc.

- **marked.min.js absent from `admin/login_base.html`.** Login pages (`login.html`, `login_2fa.html`, `forgot-password.html`, `reset-password.html`) load `main.js` but not `marked.min.js`. If any dynamically-loaded module depends on the global `marked` object, this would cause runtime errors.

- **`prefetch.js` module is undocumented.** `app/static/js/shared/prefetch.js` implements intelligent link prefetching with queue management (max 3 concurrent, max 10 queued), abort on beforeunload, and delayed prefetch on hover. It is loaded for all public pages via `main.js:74`.

- **`macros.html` contents are undocumented.** Contains a `pagination` macro (used in index.html, search.html, tag.html) and a `field_error` macro (used in admin forms). Listed in directory structure but not described.

- **`_post_content.html` partial is undocumented.** A significant partial included by `post.html:70`, `public_preview.html:10`, and `admin/preview.html:9`. Contains post hero image, share bar, TL;DR summary, markdown body rendering, author card, and back link.

- **`_error.html` partial is undocumented.** Included by `404.html:8`, `429.html:11`, and `500.html:8`. Renders error code, title, message, optional search form, and recent post suggestions.

- **`_sidebar.html` partial is undocumented.** Included by `index.html:67`, `search.html:77`, `tag.html:72`, `archive.html:58`. Shows recent posts and tags.

- **`admin/_breadcrumbs.html` macro is undocumented.** Used by most admin templates for breadcrumb navigation.

- **`data-prism-css-url` attribute on `<html>` is undocumented in architecture docs.** Set in `base.html:2`, `admin/base.html:2`, and `admin/login_base.html:2`. Used by `main.js:102` to load Prism CSS dynamically.

- **`public.css` imported in `main.js:1`** (`import '../css/public.css'`). This tells Vite to include public.css in the build graph for CSS extraction. The same CSS is also loaded via `<link>` in `base.html:27`. In production, Vite deduplicates this, but it is not documented.

- **`vite-plugin-beasties` in `package.json` but unused.** Listed as a devDependency (`"vite-plugin-beasties": "^1.0.0"`) but `vite.config.js:29` has `plugins: []`. Either it should be configured or removed.

### Potential Bugs / Concerns

- **Prism double-loading on admin pages.** `admin/base.html:162-163` loads Prism eagerly via `<script defer>`. Then `main.js:117` calls `loadPrismIfNeeded()` on DOMContentLoaded, which dynamically creates and appends a new `<script>` for `prism.min.js` and `prism-languages.js` if code blocks exist. This would load each script twice. Mitigation: `loadPrismIfNeeded()` should check if Prism is already loaded before creating new script elements.

- **marked.min.js not loaded via Vite.** Using `url_for('static', ...)` instead of `vite_asset()` means marked.min.js has no content hashing (no cache busting) and no CDN_URL support. If `CDN_URL` is configured for all other assets, marked.min.js would still be served from the origin server, creating inconsistency.

- **marked.min.js missing from login pages.** `admin/login_base.html` does not include `marked.min.js`, but does load `main.js`. If any module loaded by `main.js` on login pages references the global `marked` object, it would fail silently or throw an error.

- **admin/base.html hardcodes Prism theme to okaidia.** Regardless of the `syntax_theme` SiteSettings value, admin pages always load `prism-okaidia.css`. This could confuse admins who customize the syntax theme and expect it to apply everywhere.

- **search.html uses `| safe` on FTS5 snippets.** At `search.html:52`, `{{ search_snippets[post.id] | safe }}` renders FTS5 snippets containing `<mark>` tags without escaping. The content comes from post body text stored in the FTS table. Since only admins can create posts, the risk is low, but if a post body contains raw HTML (which markdown allows), it could be rendered in search results. The nh3 sanitization happens at display time (via `markdown_safe`), not at FTS indexing time.

- **`vite_asset()` returns `/static/` prefix for non-manifest files.** At `app/vite.py:75-78`, when a file is not in the manifest and has no hash, it returns `{base}/static/{url}`. This assumes Flask serves static files at `/static/`. If behind a reverse proxy with a different static path, this could break.

- **`inject_config()` accesses `request.path` without guarding for non-request contexts.** At `app/context_processors.py:151`, `BASE_URL.rstrip("/") + request.path` is used. Context processors only run during request handling, so this is safe in practice, but it would raise `RuntimeError` if called outside a request context (e.g., from APScheduler jobs that use templates).

- **CSS file double-loading risk.** `main.js:1` imports `../css/public.css` (Vite CSS extraction), and `base.html:27` also loads `css/public.css` via `<link>`. In production, Vite deduplicates, but during development with the Vite dev server, CSS may be injected twice (once via JS module, once via link tag), potentially causing FOUC or style conflicts.

### Improvement Suggestions

- **Fix template inheritance diagram** in `templates.md`. Show `admin/base.html` and `admin/login_base.html` as standalone templates (not extending `base.html`). Consider refactoring them to actually extend `base.html` to reduce duplication of HTML boilerplate, meta tags, theme CSS loading, and script loading.

- **Fix `loadPrismIfNeeded()` in `main.js`** to check `window.Prism` before dynamically loading scripts, preventing double-loading on admin pages.

- **Load `marked.min.js` via `vite_asset()`** instead of `url_for('static', ...)` to get content hashing and CDN support. Alternatively, add it to the Vite build graph as a vendor chunk.

- **Add `marked.min.js` to `admin/login_base.html`** if any main.js modules depend on it, or ensure modules are safe to load without it.

- **Fix `admin/base.html` Prism CSS** to use `syntax_theme` variable instead of hardcoded `prism-okaidia`, consistent with public base.html.

- **Remove or configure `vite-plugin-beasties`** in `vite.config.js` — it is listed in `package.json` but `plugins: []` is empty.

- **Document all partials** (`_post_content.html`, `_error.html`, `_sidebar.html`, `_breadcrumbs.html`) and their usage patterns in `templates.md`.

- **Document `prefetch.js`** behavior and its role in public page performance.

- **Document `macros.html`** contents (pagination, field_error macros).

- **Add `.svg` loader** to the vite.config.js code example in `static-assets.md`.

- **Fix line references** in `static-assets.md` for `vite.config.js` JSX support (31-39 should be 36-44).

- **Add warning** in docs that `marked.min.js` is loaded outside the Vite pipeline and does not benefit from content hashing or CDN.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high | Fix template inheritance diagram in `templates.md` — `admin/base.html` and `admin/login_base.html` are standalone, NOT extending `base.html` | docs |
| 2 | high | Fix Prism double-loading: `admin/base.html` loads Prism eagerly AND `loadPrismIfNeeded()` loads it dynamically again on admin pages | source |
| 3 | high | Load `marked.min.js` via `vite_asset()` instead of `url_for('static', ...)` for content hashing and CDN support | source |
| 4 | high | Fix `admin/base.html:9` to use `syntax_theme` variable for Prism CSS instead of hardcoded `prism-okaidia.css` | source |
| 5 | med | Add `marked.min.js` to `admin/login_base.html` or verify modules are safe without it | source |
| 6 | med | Update `static-assets.md` vite.config.js JSX line reference from 31-39 to 36-44 | docs |
| 7 | med | Add `.svg: 'text'` loader to vite.config.js code example in `static-assets.md` | docs |
| 8 | med | Document `prefetch.js` module, `macros.html` contents, and all template partials (`_post_content.html`, `_error.html`, `_sidebar.html`, `_breadcrumbs.html`) | docs |
| 9 | med | Document `marked.min.js` loading pattern (outside Vite pipeline) and its limitations | docs |
| 10 | med | Fix Public JS / Admin JS sections in `static-assets.md` — actual file names differ from doc descriptions (no comments.js, no newsletter.js in public/) | docs |
| 11 | low | Remove or configure unused `vite-plugin-beasties` in `vite.config.js` | source |
| 12 | low | Fix `templates.md` `public/*.html` inheritance claim — `public/comments.html` is a macro, not a page extending base.html | docs |
| 13 | low | Document `data-prism-css-url` attribute on `<html>` element and its role in Prism lazy loading | docs |
| 14 | low | Add guard in `loadPrismIfNeeded()` to check `window.Prism` existence before creating script elements | source |
| 15 | low | Consider adding search snippet sanitization (e.g., nh3 clean on FTS5 snippets before rendering with `| safe`) | source |
