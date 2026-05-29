# Frontend Architecture Review

**Reviewed:** 2026-05-29
**Architecture Docs:** architecture/frontend/overview.md, architecture/frontend/templates.md, architecture/frontend/static-assets.md
**Source Files:** app/filters.py, app/vite.py, app/context_processors.py, app/templates/*.html, app/static/js/*.js, app/static/css/*.css, vite.config.js

## Findings

### Verified Claims (Correct)

1. **Template directory structure** - All templates listed in `templates.md:6-64` exist:
   - All main templates present: base.html, index.html, post.html, archive.html, search.html, series.html, tag.html, page.html, etc.
   - Admin templates: all 27 templates present including dashboard, editor, comments, analytics, sessions, etc.
   - Email templates: base_email.html, confirm.html, newsletter.html, password_reset.html all present
   - Public partials: comments.html present

2. **Template inheritance chain** - templates.md:66-82 accurately describes inheritance:
   - base.html is public base
   - admin/base.html extends base.html
   - admin/login_base.html extends base.html
   - email/base_email.html is standalone

3. **Filters** - All filters in templates.md:84-92 verified in app/filters.py:
   - `markdown_safe` (lines 12-15): Correctly renders markdown with nh3 sanitization
   - `reading_time` (lines 17-23): Calculates reading time at 200 WPM, returns "1 min read" minimum
   - `sanitize_css` (lines 25-29): Delegates to app.utils.sanitize_css
   - `post_image_url` (lines 31-50): Uses g._post_image_cache, storage.exists() check
   - `post_image_srcset` (lines 52-76): Builds srcset for 400/800/1200 widths, uses cache
   - `post_image_avif_url_stub` (lines 78-88): DEPRECATED, always returns None

4. **Context processors** - Verified in app/context_processors.py:
   - `inject_csrf()` (lines 129-139): Provides csrf_token and csp_nonce
   - `inject_config()` (lines 142-152): Provides site_title, site_description (not site_name), author_name, author_role, author_avatar, base_url, current_year, canonical_url
   - `inject_theme()` (lines 155-156): Provides theme settings and custom_css
   - `inject_footer_data()` (lines 159-178): Provides footer posts/tags, skips admin/api/rss paths
   - `inject_show_footer_posts()` (lines 181-183): Boolean to hide footer on search/tag pages

5. **Cache invalidation functions** - Verified:
   - `invalidate_settings_cache()` (context_processors.py:30-32): Deletes site_settings cache
   - `invalidate_footer_cache()` (context_processors.py:35-37): Deletes memoized _get_footer_data

6. **CSS files** - All listed in static-assets.md:161-169 exist:
   - base.css, layout.css, public.css, forms.css, utilities.css, critical.css, admin.css
   - 6 Prism themes: prism.css, prism-dark.css, prism-coy.css, prism-funky.css, prism-okaidia.css, prism-tomorrow.css

7. **JavaScript files** - All listed in static-assets.md exist:
   - Admin: bulk.js, editor.js, shortcuts.js
   - Public: anchor-links.js, code-copy.js, lightbox.js, media-copy.js, search.js, share.js, toc.js
   - Shared: dark-mode.js, filter-select.js, lazy-load.js, mobile-menu.jsx, modal.js, nav-dropdown.js, prefetch.js, toast.js, utils.js
   - lib: marked-wrapper.js, marked.min.js
   - prism.min.js, prism-languages.js, image-preview.js, main.js, upload.js

8. **Vite chunk splitting** - vite.config.js:15-25 correctly defines:
   - vendor chunk for Prism files
   - admin chunk for admin/editor.js
   - public chunk for public/search.js

9. **Font files** - All present:
   - Inter: 300, 400, 500, 600, 700 weights (woff2)
   - JetBrains Mono: 400, 500 weights (woff2)

10. **Dark mode implementation** - dark-mode.js correctly:
    - Checks localStorage for persisted theme
    - Falls back to prefers-color-scheme
    - Sets data-theme="light" on html element when not dark
    - Listens for OS changes when no stored preference

11. **Critical CSS loading** - base.html:24 correctly loads critical.css with `media="screen"` for immediate rendering

12. **Prism lazy loading** - main.js:97-112 correctly lazy-loads Prism only when code blocks present

13. **Lazy image loading** - lazy-load.js correctly implements 3-tier fallback:
    - Native support check first
    - IntersectionObserver polyfill second
    - Immediate load fallback third

### Discrepancies (Doc vs Code)

1. **Vite asset helper line number** - static-assets.md:206 states `vite_asset()` is at `app/vite.py:48` but actually at line 48 (correct), registered via `init_vite()` at lines 81-83. This is accurate.

2. **Syntax theme loading** - static-assets.md:193 says "lazy-loaded by main.js:97-112" - verified correct in main.js:97-112, however main.js:102 uses `/static/css/` path directly (not vite_asset), while admin/base.html:9 uses vite_asset for prism CSS. This is an inconsistency but not a bug.

3. **Context processor line numbers** - templates.md:110-111 says `invalidate_settings_cache()` is at "line 30-32" and `invalidate_footer_cache()` at "line 35-37". Code shows:
   - invalidate_settings_cache: lines 30-32 (correct)
   - invalidate_footer_cache: lines 35-37 (correct)

4. **Admin base template body class** - static-assets.md:131 mentions `document.body.classList.contains('admin-body')` for admin detection. Verified in admin/base.html:28 and login_base.html:27 - both use `admin-body` class on body element.

5. **mobile-menu.jsx in glob** - static-assets.md:26 mentions mobile-menu.jsx as JSX file. Verified present at app/static/js/shared/mobile-menu.jsx. The docs say it's included in the shared modules.

6. **Dark mode line numbers** - static-assets.md:173-178 describes dark-mode.js functionality, verified against actual code at dark-mode.js:1-50. All description points match.

7. **Image skeleton CSS line numbers** - static-assets.md:117-119 references public.css:1114-1138 for .img-skeleton shimmer animation. Actual code at public.css:1114-1138 matches this exactly.

### Missing Documentation

1. **email/base_email.html** - Standalone template not extending base.html (does not use vite_asset), documented correctly but worth noting it uses inline styles for email compatibility.

2. **login_base.html CSS loading** - admin/login_base.html:8-13 uses `url_for('static', ...)` directly instead of `vite_asset()`. This is a deviation from the pattern used in base.html and admin/base.html.

3. **marked.min.js loading** - base.html:150 and admin/base.html:164 load marked.min.js via `url_for('static', ...)` not vite_asset. This is consistent with marked.js being a non-Vite library.

4. **JS module init pattern** - main.js:85-96 calls `module.default()` if it exists. The documentation at static-assets.md:49-59 correctly describes this pattern. Modules without default export are silently ignored.

5. **_post_image_cache structure** - filters.py:36-46 uses g._post_image_cache as dict with post_id keys for post_image_url, but also stores srcset cache with key `_post_srcset_cache_{post.id}` (line 57). This is an implementation detail worth documenting.

6. **Prism syntax theme attribute** - base.html:2 sets `data-syntax-theme="{{ syntax_theme or 'okaidia' }}"` on html element. This allows JS to dynamically load the correct theme via main.js:102.

### Potential Bugs / Concerns

1. **Inconsistent asset loading in login templates** - admin/login_base.html (lines 8-13, 56-58) uses `url_for('static', ...)` directly while admin/base.html uses `vite_asset()`. This means login pages don't get content-hashed URLs or CDN prefix support. Login pages are unlikely to have cache issues since they're not heavily cached, but inconsistency could cause issues if assets change.

2. **Prism theme loading inconsistency** - base.html:30 uses `vite_asset('css/' + syntax_theme + '.css')` but main.js:102 loads Prism CSS via direct path `/static/css/${document.documentElement.dataset.syntaxTheme || 'okaidia'}.css`. If CDN_URL is configured, the JS path won't include it, potentially causing mismatched asset origins.

3. **marked.min.js not in Vite manifest** - marked.min.js is loaded directly via url_for, not through Vite's build system. This means it's not content-hashed and won't benefit from Vite's optimization.

4. **No error handling for missing Vite manifest** - vite.py:26-30 silently returns empty dict if manifest doesn't exist. In production, if Vite build hasn't run, JS assets will return hashed paths that don't exist.

5. **CSS hash caching** - vite.py:36-45 caches file hashes in _css_hash_cache dict. This is process-level caching that won't update if files change without restart.

### Improvement Suggestions

1. **Standardize login template asset loading** - Consider using vite_asset() consistently in admin/login_base.html for consistency and CDN support.

2. **Document Vite build requirement** - The architecture docs should note that `npm run build` (or vite build) must be run before production deployment, and the manifest.json must be present.

3. **Add template filter usage examples** - The templates.md could benefit from showing actual usage of filters in templates (e.g., `{{ post|post_image_url }}` shown in index.html:21).

4. **Document CSS loading pattern** - The `media="print" onload="this.media='all'"` pattern for deferred CSS loading could be documented as a performance optimization.

5. **Consider adding mobile-menu.jsx to docs** - The JSX file is mentioned in static-assets.md but could use more detail on how Vite handles it.

6. **Document cache invalidation triggers** - When and why cache invalidation functions are called (e.g., on settings change) would be helpful for maintenance.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | medium | Login templates (admin/login_base.html) use url_for instead of vite_asset, creating inconsistency and missing CDN support | code |
| 2 | medium | Prism CSS loaded via JS (main.js:102) bypasses vite_asset, missing CDN prefix | code |
| 3 | low | marked.min.js loaded outside Vite build system, not content-hashed | code |
| 4 | low | _post_image_cache implementation detail (post_id keys vs `_post_srcset_cache_{post.id}` keys) undocumented | docs |
| 5 | low | Consider documenting that Vite build must run before production | docs |
