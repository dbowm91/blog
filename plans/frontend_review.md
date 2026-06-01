# Frontend Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** overview.md, templates.md, static-assets.md
**Source Files:** app/templates/, app/static/, app/filters.py, app/vite.py, app/context_processors.py

## Findings

### Verified Claims (Correct)

1. **Template filter registry** — `app/filters.py` registers exactly 6 filters: `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`. All documented descriptions match implementation (templates.md:86-92).

2. **Context processors** — `app/context_processors.py` defines all documented processors: `inject_csrf`, `inject_config`, `inject_theme`, `inject_footer_data`, `inject_show_footer_posts`. Variable names `site_title` and `site_description` are correct (not `site_name`/`site_tagline`) — `context_processors.py:144-145`.

3. **Cache invalidation functions** — `invalidate_settings_cache()` (line 30-32) and `invalidate_footer_cache()` (line 35-37) match docs exactly.

4. **`data-prism-css-url` attribute** — `base.html:2` includes `data-prism-css-url="{{ vite_asset('css/' + syntax_theme + '.css') }}"`. The `loadPrismIfNeeded()` function in `main.js:97-112` reads this attribute and dynamically injects the Prism CSS. Verified.

5. **Critical CSS loading** — `base.html:24` loads `critical.css` with `media="screen"` for immediate rendering. Other stylesheets use `media="print" onload="this.media='all'"`. Matches docs (static-assets.md:202).

6. **Vite asset helper** — `app/vite.py:48` `vite_asset()` resolves content-hashed URLs via manifest lookup (JS) or MD5 query strings (CSS/other). Registered as Jinja2 global at `app/vite.py:81-83`. Matches docs (static-assets.md:228).

7. **JS module initialization pattern** — `main.js:85-96` checks `typeof module.default === 'function'` and calls it. Matches docs (static-assets.md:51-59).

8. **Route-based code splitting** — `main.js:30-83` implements `ROUTE_MODULES` and `getModulesForPath()` matching docs (static-assets.md:62-103).

9. **Vite config** — `vite.config.js` entry point, output, manualChunks, esbuildOptions for JSX, and dev server port all match docs (static-assets.md:217-223, 146-161).

10. **Font preloading** — `base.html:39-40` preloads Inter and JetBrains Mono woff2 fonts with `crossorigin`. Matches docs (static-assets.md:209).

11. **Dark mode** — `dark-mode.js` implementation with `data-theme="light"`, localStorage, and `prefers-color-scheme` matches docs (static-assets.md:193-198).

12. **post_image_srcset filter** — Checks widths 400, 800, 1200 and builds `srcset` with width descriptors. Uses `g._post_image_cache` for request-level caching. Matches docs (templates.md:91).

13. **post_image_avif_url_stub** — Always returns `None`, deprecated. Matches docs (templates.md:92).

### Discrepancies (Doc vs Code)

1. **`admin/base.html` does NOT extend `base.html`** — `templates.md:71` claims `admin/base.html` extends `base.html`. In reality, `admin/base.html:1` starts with `<!DOCTYPE html>` and is a completely standalone template. It duplicates the full HTML document structure including its own `<head>`, navbar, flash messages, footer, and script loading. This is a significant documentation error.

2. **`admin/login_base.html` does NOT extend `base.html`** — `templates.md:73` claims `admin/login_base.html` extends `base.html`. It is also standalone with `<!DOCTYPE html>` at line 1. Another significant documentation error.

3. **`marked.min.js` is loaded via `vite_asset()`, NOT `url_for('static', ...)`** — `static-assets.md:135-139` claims `marked.min.js` is loaded outside the Vite pipeline via `url_for('static', ...)`. Both `base.html:150` and `admin/base.html:162` actually use `{{ vite_asset('js/lib/marked.min.js') }}`. The doc is wrong — `marked.min.js` DOES go through Vite's asset pipeline and gets proper content hashing and CDN support.

4. **Admin base does NOT load `critical.css`** — `admin/base.html` does not include `critical.css` at all. The docs only mention `critical.css` in context of `base.html:24` (static-assets.md:202), which is correct, but the omission from admin is undocumented.

5. **`admin/login_base.html` loads Prism JS statically, not lazily** — `login_base.html:56-57` loads `prism.min.js` and `prism-languages.js` directly via `<script defer>`, bypassing the `loadPrismIfNeeded()` lazy-load pattern used by `base.html` and `admin/base.html`. The docs (static-assets.md:213) state "Prism.js itself is lazy-loaded by `main.js:97-112` only when code blocks are present" — this is not true for login pages.

6. **`admin/login_base.html` hardcodes Prism CSS theme** — `login_base.html:8` loads `css/prism-okaidia.css` directly instead of using the `syntax_theme` context variable like `base.html:30` and `admin/base.html:9`. This means the login page ignores the user's configured syntax theme.

7. **Prism theme CSS filenames** — `static-assets.md:189` lists `prism-okaidia.css` but the actual glob result shows the file is `prism-okaidia.css` (matching). However, the docs list it as one of six themes: `prism.css`, `prism-dark.css`, `prism-coy.css`, `prism-funky.css`, `prism-okaidia.css`, `prism-tomorrow.css`. Verified correct against `app/static/css/prism-*.css`.

8. **`post_image_srcset` filter builds hardcoded `/static/uploads/` path** — `filters.py:72` hardcodes `f"{base_url.rstrip('/')}/static/uploads/{variant_name}"` for srcset URLs instead of using `vite_asset()` or `url_for('static', ...)`. The docs don't mention this hardcoding. This could break if the static file serving path changes.

9. **Missing `prism.min.js`/`prism-languages.js` from `import.meta.glob`** — `main.js:6-28` lists all modules for code splitting, but `prism.min.js` and `prism-languages.js` are NOT in the glob. This is correct behavior (they're loaded dynamically by `loadPrismIfNeeded()`), but the docs don't explain this deliberate exclusion.

### Missing Documentation

1. **`admin/base.html` standalone structure** — No documentation explains that `admin/base.html` is a fully independent template duplicating the public base structure. This is an important architectural detail for anyone modifying templates.

2. **Template duplication across base templates** — Three standalone base templates (`base.html`, `admin/base.html`, `admin/login_base.html`) each contain their own `<!DOCTYPE>`, `<head>`, CSS loading, theme injection, flash messages, and script loading. The docs show an inheritance hierarchy that doesn't exist.

3. **Login page Prism bypass** — No documentation explains that `login_base.html` bypasses lazy Prism loading and hardcodes the Prism CSS theme.

4. **`post_image_srcset` hardcoded path** — The filter at `filters.py:72` constructs srcset URLs with a hardcoded `/static/uploads/` prefix. No docs mention this or explain why it doesn't use `vite_asset()`.

5. **`inject_footer_data()` path exclusions** — `context_processors.py:161` excludes `/admin`, `/api`, and `/rss` paths from footer data loading. Not documented.

6. **`inject_show_footer_posts()` behavior** — `context_processors.py:183` hides footer posts on `/search` and `/tag/` paths. Not documented in architecture docs.

7. **`prism.min.js`/`prism-languages.js` not in `import.meta.glob`** — The deliberate exclusion from the static glob (for dynamic loading) is not explained in docs.

8. **`marked.min.js` loaded in admin base too** — Both `base.html:150` and `admin/base.html:162` load `marked.min.js` via `vite_asset()`. No docs mention this for admin.

### Potential Bugs / Concerns

1. **Admin CSS lacks `critical.css`** — `admin/base.html` doesn't load `critical.css`, meaning admin pages miss above-the-fold optimization. The `media="print" onload="this.media='all'"` deferred loading pattern is also absent — all admin CSS loads synchronously. This could cause slower initial paint on admin pages.

2. **`post_image_srcset` hardcoded path** — `filters.py:72` hardcodes `/static/uploads/` in srcset URLs. If the uploads directory path changes or if a CDN prefix should apply to these URLs, the srcset will serve broken image references. Should use `url_for('static', ...)` or a storage-aware URL builder.

3. **`login_base.html` hardcoded Prism theme** — `login_base.html:8` always loads `prism-okaidia.css` regardless of the user's `syntax_theme` setting. If a user configures a different Prism theme, login pages will flash the wrong syntax highlighting theme.

4. **`login_base.html` loads Prism JS eagerly** — `login_base.html:56-57` loads `prism.min.js` and `prism-languages.js` on every login page even though login pages don't contain code blocks. This is unnecessary JS bloat on auth pages.

5. **`post_image_srcset` returns `None` outside request context** — `filters.py:76` returns `None` if `has_request_context()` is false. This means email templates or other non-request contexts will never get srcset attributes, even if images exist. This may be intentional but is undocumented.

6. **Three standalone base templates** — The triple duplication of HTML boilerplate (head, CSS loading, theme injection, flash messages, scripts) across `base.html`, `admin/base.html`, and `login_base.html` creates maintenance risk. A change to the theme injection block or flash message handling must be replicated in all three files.

7. **`loadPrismIfNeeded()` hardcodes Prism paths** — `main.js:106,109` hardcodes `/static/js/prism.min.js` and `/static/js/prism-languages.js` without using `vite_asset()`. In production, these paths may not exist if Vite build hasn't run, or they won't benefit from content hashing/CDN.

### Improvement Suggestions

1. **Extract shared base template** — Create a `_root.html` partial containing the common `<head>`, theme injection, flash messages, and script loading blocks. Have all three base templates include it via `{% include %}` to reduce duplication.

2. **Add `critical.css` to admin base** — Admin users also benefit from fast above-the-fold paint. Add `critical.css` with `media="screen"` to `admin/base.html`.

3. **Use `vite_asset()` for Prism JS in `loadPrismIfNeeded()`** — `main.js:106,109` should use a data attribute or Vite-resolved URL instead of hardcoding `/static/js/prism.min.js`.

4. **Make `login_base.html` use `syntax_theme` variable** — Replace `css/prism-okaidia.css` with `css/{{ syntax_theme }}.css` to respect user configuration.

5. **Lazy-load Prism JS on login pages** — Either remove the static Prism script tags from `login_base.html` and rely on `loadPrismIfNeeded()`, or remove them entirely since login pages have no code blocks.

6. **Fix `post_image_srcset` to use dynamic base URL** — Replace the hardcoded `/static/uploads/` path with a storage-aware URL builder or `url_for('static', ...)`.

7. **Document the standalone template architecture** — Update `templates.md` to accurately reflect that `admin/base.html` and `admin/login_base.html` are standalone, not extending `base.html`.

8. **Document `marked.min.js` uses `vite_asset()`** — Correct `static-assets.md` to state that `marked.min.js` is loaded through the Vite pipeline via `vite_asset()`.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | High | Fix `templates.md` — `admin/base.html` and `login_base.html` are standalone, not extending `base.html` | templates.md |
| 2 | High | Fix `static-assets.md` — `marked.min.js` uses `vite_asset()`, not `url_for('static', ...)` | static-assets.md |
| 3 | Medium | Make `login_base.html` use `syntax_theme` variable instead of hardcoded `prism-okaidia.css` | admin/login_base.html:8 |
| 4 | Medium | Use `vite_asset()` for Prism JS paths in `main.js:106,109` instead of hardcoded `/static/js/` | app/static/js/main.js |
| 5 | Medium | Fix `post_image_srcset` hardcoded `/static/uploads/` path in `filters.py:72` | app/filters.py:72 |
| 6 | Low | Add `critical.css` to `admin/base.html` for faster admin page paint | admin/base.html |
| 7 | Low | Document standalone template architecture and login page Prism behavior in templates.md | templates.md |
| 8 | Low | Remove unnecessary `prism.min.js`/`prism-languages.js` from `login_base.html` (no code blocks on login pages) | admin/login_base.html:56-57 |
