# Frontend Architecture Review

**Reviewed:** 2026-06-02
**Architecture Docs:** architecture/frontend/overview.md, architecture/frontend/templates.md, architecture/frontend/static-assets.md
**Source Files:** app/filters.py, app/vite.py, app/context_processors.py, app/templates/base.html, app/templates/admin/base.html, app/templates/admin/login_base.html, app/templates/email/base_email.html, app/static/js/main.js, vite.config.js

## Findings

### Verified Claims (Correct)

- **Template inheritance hierarchy** - Correctly documented: 4 standalone base templates (`base.html`, `admin/base.html`, `admin/login_base.html`, `email/base_email.html`), each with own DOCTYPE and full HTML skeleton, NOT extending each other
- **Jinja2 filters registered in `app/filters.py`** - All 6 documented filters exist and are correctly registered:
  - `markdown_safe` (lines 12-15): renders markdown with nh3 sanitization
  - `reading_time` (lines 17-23): calculates reading time from word count
  - `sanitize_css` (lines 25-29): delegates to `app.utils.sanitize_css`
  - `post_image_url` (lines 31-50): uses `g._post_image_cache` for request-level caching
  - `post_image_srcset` (lines 52-75): generates srcset for 400, 800, 1200 width variants
  - `post_image_avif_url_stub` (lines 77-87): DEPRECATED, always returns None
- **Context variables** - `site_title` and `site_description` used (NOT `site_name`/`site_tagline`) in `context_processors.py:144-145`
- **Critical CSS loading** - `base.html:24` and `admin/base.html:9` both load `critical.css` with `media="screen"`
- **Prism lazy loading via `data-prism-*` attributes** - `base.html:2` and `admin/base.html:2` have `data-prism-css-url`, `data-prism-js-url`, `data-prism-langs-url`; consumed by `main.js:97-112` `loadPrismIfNeeded()`
- **`vite_asset()` function** - `app/vite.py:48-78` correctly resolves content-hashed URLs with CDN support
- **Template directory structure** - All listed templates exist at documented paths
- **Static JS/CSS directory structure** - All listed files exist at documented paths
- **`mobile-menu.jsx` exists** at `app/static/js/shared/mobile-menu.jsx`
- **Dark mode OS preference detection** - `dark-mode.js:13-14` uses `prefers-color-scheme: dark` media query
- **Lazy loading three-tier fallback** - `lazy-load.js:1-32` implements native lazy loading, IntersectionObserver polyfill, immediate load fallback
- **Vite chunk splitting** - `vite.config.js:15-25` creates `vendor`, `admin`, `public` chunks
- **marked.min.js loading** - Loaded via `vite_asset('js/lib/marked.min.js')` in `base.html:150` and `admin/base.html:163`
- **JSX support via esbuildOptions** - `vite.config.js:36-44` configures `.jsx` loader

### Discrepancies (Doc vs Code)

| File | Line | Documentation Claim | Actual Code |
|------|------|---------------------|-------------|
| `static-assets.md` | 131 | "Observes link visibility via IntersectionObserver" for prefetch | `prefetch.js:39-50` uses `mouseenter` event listeners with debounce timer, NOT IntersectionObserver |
| `static-assets.md` | 209-210 | "Theme CSS is loaded dynamically in `base.html:30`" | Prism theme CSS is on `base.html:30` as `media="print" onload="this.media='all'"` |
| `static-assets.md` | 51 | "module loader in `main.js:85-96` calls `module.default()`" | `main.js:85-96` is the `loadModule` function; `module.default()` call is at line 89 |
| `templates.md` | 135 | Lists `paginate(pagination)` and `field_error(field)` macros | `macros.html` also contains `badge(text, class='badge')` macro (line 71-73) - undocumented |
| `templates.md` | 63 | Directory shows `public/` but only comments.html exists | `app/templates/public/comments.html` exists but is not listed in directory tree |
| `static-assets.md` | 136 | "marked.min.js is loaded...in both `base.html:150` and `admin/base.html:162`" | `admin/base.html:163` is the actual line (doc says 162) |
| `static-assets.md` | 206 | "Preloaded in `base.html:39-40`" | Actual lines are `base.html:39-40` for Inter and JetBrains Mono woff2 fonts |

### Missing Documentation

1. **`badge` macro** - `macros.html:71-73` defines a `badge(text, class='badge')` macro not mentioned in docs
2. **`public/comments.html` location** - Located at `app/templates/public/comments.html` but not shown in directory structure
3. **`prefetch.js` actual mechanism** - Uses `mouseenter` with debounce, not IntersectionObserver visibility
4. **Login template asset loading** - `admin/login_base.html` uses `vite_asset()` for CSS/JS (line 8, 56) but this is not documented
5. **Admin Prism CSS theme selection** - `admin/base.html:10` uses `syntax_theme` variable for dynamic Prism theme via `vite_asset('css/' + syntax_theme + '.css')` but not explicitly documented
6. **`_sidebar.html` usage** - Used by public templates (e.g., `index.html:67`), not just admin as directory structure implies
7. **Font files actually preloaded** - `inter-400-latin.woff2` and `jetbrains-mono-400-latin.woff2` at `base.html:39-40` with `crossorigin` attribute
8. **Email templates do NOT use `vite_asset()`** - `email/base_email.html` uses plain `<link>` tags, no content hashing or CDN support

### Potential Bugs / Concerns

1. **`post_image_srcset` no-request-context returns None** (`filters.py:75`)
   - When `has_request_context()` is False, `post_image_srcset` returns `None` while `post_image_url` falls back to non-cached storage check
   - Inconsistency: `post_image_url` handles no-request-context (line 47-50), `post_image_srcset` does not

2. **`vite_asset` fallback inconsistency** (`vite.py:78`)
   - When manifest lookup fails AND file hash not found: returns `f"{base}/static/{url}"`
   - But when manifest lookup succeeds: returns `f"{base}/static/dist/{hashed_path}"`
   - If CDN_URL is set, `base` is prepended in both cases, but the path structure differs (`dist/` vs no `dist/`)

3. **Deprecated filter still registered** - `post_image_avif_url_stub` is marked DEPRECATED in doc and code comments but still registered as a template filter, adding overhead

4. **`_get_cached_settings` caches fallback on DB error** (`context_processors.py:77-89`)
   - On `OperationalError`, returns hardcoded fallback and caches it
   - Cache is not invalidated on database recovery; stale fallback persists for `timeout=300`

5. **`_get_footer_data` caches empty fallback on DB error** (`context_processors.py:171-178`)
   - On `OperationalError`, returns empty lists and caches them for 45 seconds
   - Stale empty data shown until cache expires after DB recovery

6. **Lazy load `.loaded` class inconsistency** (`lazy-load.js`)
   - Native lazy loading path (line 3-4) returns early without adding `.loaded` class
   - IntersectionObserver path (line 25) does add `.loaded` class
   - CSS at `public.css:1115-1123` expects `.loaded` class for opacity transition, but native path never adds it
   - **Note**: This may be intentional since native lazy loading browser handles opacity via `loading="lazy"` attribute

7. **Prefetch URL validation missing** (`prefetch.js:31`)
   - Only checks for `mailto:` and `tel:` protocols
   - Does NOT validate for `javascript:` or `data:` URLs which could cause issues
   - Could potentially prefetch internal URLs that shouldn't be prefetched

8. **CSS deferred loading on admin templates** (`admin/base.html:9-15`)
   - Admin templates load CSS immediately without `media="print" onload="this.media='all'"` deferral
   - Public templates use deferred loading pattern; admin templates load synchronously
   - May cause slower initial admin page renders

### Improvement Suggestions

1. **Add `badge` macro to documentation** in `templates.md` under "Reusable Jinja2 macros"

2. **Fix `prefetch.js` description** in `templates.md:131` - change "observes link visibility via IntersectionObserver" to "uses mouseenter event listeners with 100ms debounce"

3. **Update line references** that have drifted:
   - `admin/base.html` marked.min.js line is 163, not 162
   - Consider using relative ranges like "lines 85-89" instead of exact lines

4. **Add missing documentation for**:
   - `public/comments.html` location
   - Login template `vite_asset()` usage
   - Admin template Prism theme selection
   - Font file names (inter-400-latin.woff2, jetbrains-mono-400-latin.woff2)

5. **Consider standardizing CSS loading** between public and admin templates - either both use deferred loading or both use immediate loading

6. **Add SSRF protection validation to `prefetch.js`** - validate prefetched URLs don't use `javascript:` or `data:` protocols

7. **Consider adding error handling wrapper** for `_get_cached_settings` and `_get_footer_data` that clears cache on database errors instead of caching the error state

8. **Add cache invalidation on database recovery** - when `OperationalError` occurs, subsequent successful DB reads should invalidate the cached error fallback

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | med | Fix `prefetch.js` description - it uses mouseenter, not IntersectionObserver | docs |
| 2 | med | Document `badge` macro in `macros.html` | docs |
| 3 | med | Update line references that have drifted (admin/base.html marked.min.js: 162 -> 163) | docs |
| 4 | low | Add `public/comments.html` to directory structure | docs |
| 5 | low | Document login template `vite_asset()` usage | docs |
| 6 | med | Standardize CSS loading between admin and public templates | code |
| 7 | low | Add URL protocol validation to `prefetch.js` | code |
| 8 | med | Consider cache invalidation on database error recovery for `_get_cached_settings` and `_get_footer_data` | code |
