# Frontend Architecture Review

## Summary

Reviewed architecture documents in `architecture/frontend/` (overview.md, static-assets.md, templates.md) and corresponding implementation files in `app/static/` and `app/templates/`, including AGENTS.override.md files for both modules.

---

## Verified Accurate Claims

### JavaScript Organization
- Directory structure matches: `js/admin/`, `js/public/`, `js/shared/`, `js/lib/`
- JSX file `mobile-menu.jsx` correctly listed in `shared/` with JSX support via Vite esbuildOptions
- Module initialization pattern correctly documented: modules must export `default initXxx` function
- Route-based code splitting via `import.meta.glob()` in `main.js:6-28` and `ROUTE_MODULES` at lines 30-62
- Admin body class detection via `document.body.classList.contains('admin-body')` is accurate

### Vite Configuration
- Entry point: `app/static/js/main.js` (verified in `vite.config.js:12`)
- Output directory: `app/static/dist/` (verified in `vite.config.js:7`)
- Code splitting via `manualChunks`: vendor (prism), admin (editor.js), public (search.js) - verified at lines 15-19
- JSX support via `optimizeDeps.esbuildOptions.loader` for `.jsx` files (lines 30-35)
- Dev server on port 3000 with proxy to Flask on port 5000 (lines 24-28)

### CSS Architecture
- Self-hosted fonts (Inter 300-700, JetBrains Mono 400-500) via `@font-face` in `base.css:6-60`
- No external font CDNs - all fonts in `app/static/fonts/`
- Dark mode is default; light theme toggled via `data-theme` attribute on `<html>` (base.css:181)
- 6 syntax highlighting themes: prism, prism-coy, prism-dark, prism-funky, prism-okaidia, prism-tomorrow

### Content Hashing
- Vite generates content-hashed filenames (verified in `dist/` directory)
- Manifest file at `app/static/dist/.vite/manifest.json`
- Flask helper `vite_asset()` in `app/vite.py` correctly handles JS lookup from manifest and CSS hash appending
- Templates use `{{ vite_asset('path') }}` instead of `{{ url_for('static', ...) }}`

### Template Filters (app/filters.py)
- `markdown_safe` - Render markdown with nh3 sanitization (lines 12-17)
- `reading_time` - Calculate reading time (lines 19-25)
- `sanitize_css` - Sanitize custom CSS (lines 27-31)
- `post_image_url` - Get post image URL with request-level caching via Flask `g` object (lines 33-50)
- `post_image_srcset` - Generate srcset for responsive images (lines 52-73)
- `post_image_avif_url_stub` - Returns None (DEPRECATED filter, lines 75-85)

### Context Processors (app/context_processors.py)
- `inject_csrf()` - Injects `csrf_token` and `csp_nonce` (lines 138-148)
- `inject_config()` - Injects `site_title`, `site_description`, `author_name`, `author_role`, `author_avatar`, `base_url`, `current_year`, `canonical_url` (lines 150-161)
- `inject_theme()` - Injects theme settings and `custom_css` (lines 163-165)
- `inject_footer_data()` - Footer links and data (lines 167-191)
- `inject_show_footer_posts()` - `show_footer_posts` boolean (lines 193-200)
- `invalidate_settings_cache()` and `invalidate_footer_cache()` functions present (lines 30-37)

### Template Structure
- Base template `base.html` correctly extends to public templates
- Admin templates extend `admin/base.html`
- Macro file `macros.html` contains pagination and field_error macros

---

## Discrepancies and Issues

### 1. templates.md Lists Non-Existent Templates

**Issue:** `templates.md` directory structure lists files that don't exist:
- `admin/posts.html` - Should be `admin/editor.html`
- `admin/post_edit.html` - Should be `admin/editor.html`
- `admin/newsletter.html` - Does not exist

**Actual admin templates:**
- `editor.html` (for posts)
- `page_editor.html` (for pages)
- `series_editor.html`
- No newsletter admin template exists

### 2. templates.md Uses Wrong Variable Names

**Issue:** The "Context Processors" section incorrectly documents:
- `site_name` instead of `site_title`
- `site_tagline` instead of `site_description`

**Actual (from context_processors.py:150-161):**
```python
"site_title": APP_TITLE,
"site_description": APP_DESCRIPTION,
```

### 3. templates.md Missing critical.css

**Issue:** The CSS section says "Base styles, Component styles, Theme-specific styles" but does not list `critical.css`, which exists at `app/static/css/critical.css` and is used in `base.html:22`.

### 4. app/templates/AGENTS.override.md Has Incorrect Structure

**Issue:** The template structure in `app/templates/AGENTS.override.md` lists non-existent files:
- `admin/posts.html` and `admin/post_edit.html` should reference `admin/editor.html`
- `admin/newsletter.html` does not exist
- `public/subscribe.html` does not exist (only `public/comments.html` exists)
- Missing many actual templates like `admin/backup_codes.html`, `admin/2fa_setup.html`, `admin/2fa_verify.html`, `admin/disable_2fa.html`, etc.

### 5. app/static/AGENTS.override.md Missing critical.css

**Issue:** The CSS section in `app/static/AGENTS.override.md` lists `base.css`, `layout.css`, `forms.css`, `admin.css`, `public.css`, `utilities.css`, `prism.css`, `prism-*.css` but does NOT include `critical.css`.

### 6. static-assets.md Module List Incomplete

**Issue:** The module listing in `static-assets.md` (lines 30-31) shows shared modules but misses:
- `upload.js` - Admin upload handler
- `image-preview.js` - Admin image preview

### 7. Route-Based Code Splitting Documentation Slightly Misleading

**Issue:** `static-assets.md` states (line 76):
> "Admin pages get utils, modal, shortcuts, bulk."

Looking at `main.js:53-61`, admin routes (`/admin/`) include:
```javascript
'./shared/utils.js',
'./shared/modal.js',
'./shared/nav-dropdown.js',
'./shared/filter-select.js',
'./shared/toast.js',
'./admin/shortcuts.js',
'./admin/bulk.js',
```

But does NOT include `dark-mode.js`, `mobile-menu.jsx`, `lazy-load.js`, `prefetch.js`, or any public modules. The documentation is incomplete.

### 8. AGENTS.override.md Module Pattern Description Slightly Off

**Issue:** `app/static/AGENTS.override.md` says (lines 54-56):
> "When adding new modules to `shared/` or `public/`, you **must** add `export default initXxx;`"

This implies the function name must be `init` + module name. But looking at actual modules:
- `toast.js` exports `initToast` and also `showToast` (named export)
- `dark-mode.js` exports `initDarkMode`
- `utils.js` exports `initSharedUtils` (not `initUtils`)

The pattern is more flexible than stated - it should be `export default init<Something>` where `<Something>` is descriptive, not necessarily the filename.

### 9. search.html Template srcset Issue

**Issue:** In `search.html:32`:
```html
<img ... srcset="{{ srcset }}" sizes="(max-width: 600px) 400px, 800px" ...>
```

The `sizes` attribute is hardcoded but should be responsive. More importantly, `srcset` uses `/static/uploads/` path via `url_for`, but according to `vite_asset()` implementation, this bypasses the content-hashed URL system. However, since these are user-uploaded images (not processed by Vite), this is likely intentional but undocumented.

### 10. Image Caching Logic Different Than Documented

**Issue:** `app/templates/AGENTS.override.md` says (lines 66-79):
> "The `post_image_url` filter uses Flask `g` object for request-level caching"

But the actual implementation in `filters.py:33-50` uses `storage.exists()` and is more complex. The description is incomplete - it doesn't mention the `storage.exists()` check or the fallback when outside request context.

---

## Bugs

### Bug 1: CSS media="print" onload Pattern May Cause Issues

In `base.html:23-27`:
```html
<link rel="stylesheet" href="{{ vite_asset('css/base.css') }}" media="print" onload="this.media='all'">
```

This pattern loads CSS with `media="print"` and switches to `media="all"` on load. While this works for FOUC prevention, the `media="print"` may cause the stylesheet to be deprioritized or skipped in some browsers' preload scanners.

**Recommendation:** Consider using `media="screen"` with `preload` + `onload` pattern instead, or document why `media="print"` was chosen.

### Bug 2: Prism Theme Loading Race Condition

In `main.js:97-112`, `loadPrismIfNeeded()` is called after DOMContentLoaded but inserts CSS/JS synchronously:
```javascript
const prismCSS = document.createElement('link');
prismCSS.href = `/static/css/${document.documentElement.dataset.syntaxTheme || 'okaidia'}.css`;
document.head.appendChild(prismCSS);
```

This happens after other modules have already run. If a post has code blocks and theme hasn't loaded yet, there could be a flash of unstyled code. This is a minor issue but worth noting.

---

## Security Concerns

### Security 1: CSP Nonce Usage in Inline Scripts

In `base.html:39-50`, `admin/base.html:15-26`:
```html
<style nonce="{{ csp_nonce }}">
    :root {
        {% for key, value in theme_vars.items() %}
        ...
        {% endfor %}
    }
    {% if custom_css_enabled and custom_css %}
    {{ custom_css | sanitize_css | safe }}
    {% endif %}
</style>
```

The `custom_css | sanitize_css | safe` pattern could be risky if `sanitize_css` has any edge cases. The `nh3` library is used for markdown sanitization, but CSS sanitization is a different beast. However, looking at `app/utils.py:sanitize_css()`, this appears to be a allowlist-based approach which is good.

**Note:** This is not a bug - the sanitization appears correct - but the pattern warrants careful review if CSS sanitization rules change.

### Security 2: Image Preview Module Import Name Mismatch

The AGENTS.md notes:
> "image-preview.js Not image-review.js - The admin image preview module is named `image-preview.js`, NOT `image-review.js`. Code imports in `main.js:15,40,51` reference the wrong filename."

Looking at `main.js:15`:
```javascript
'./image-preview.js',
```

This appears correct in the current code. The issue was previously fixed. **No action needed.**

---

## Recommended Improvements

### 1. Update templates.md Directory Structure

Replace the directory structure section with accurate file listings. The current version lists non-existent files.

### 2. Fix templates.md Context Processors Section

Change:
- `site_name` to `site_title`
- `site_tagline` to `site_description`

### 3. Add critical.css to Documentation

Add `critical.css` to the CSS file listings in both `static-assets.md` and `app/static/AGENTS.override.md`.

### 4. Update app/templates/AGENTS.override.md Structure

The template structure is outdated and lists many non-existent files. Should match actual template inventory.

### 5. Document Image URL Handling

The `post_image_url` filter uses `storage.exists()` which may use S3 or local storage depending on configuration. This should be documented.

### 6. Clarify Route-Based Code Splitting

Update `static-assets.md` to accurately list which modules load on admin routes vs public routes.

### 7. Add vscode/suggestions to .gitignore

The `app/static/dist/` contains built files. Ensure `.gitignore` properly excludes these but includes `.vite/manifest.json` for production deployments.

### 8. Document Lazy Loading Strategy

The `lazy-load.js` only activates when `loading` attribute is NOT in HTMLImageElement.prototype. This fallback behavior should be documented.

---

## Files Verified

### Architecture Documents
- `/Users/davidbowman/projects/blog/architecture/frontend/overview.md` - Mostly accurate
- `/Users/davidbowman/projects/blog/architecture/frontend/static-assets.md` - Incomplete, some inaccuracies
- `/Users/davidbowman/projects/blog/architecture/frontend/templates.md` - Lists non-existent files

### Implementation Files
- `/Users/davidbowman/projects/blog/vite.config.js` - Accurate
- `/Users/davidbowman/projects/blog/app/vite.py` - Accurate
- `/Users/davidbowman/projects/blog/app/filters.py` - Accurate
- `/Users/davidbowman/projects/blog/app/context_processors.py` - Accurate
- `/Users/davidbowman/projects/blog/app/static/js/main.js` - Accurate
- `/Users/davidbowman/projects/blog/app/templates/base.html` - Accurate
- `/Users/davidbowman/projects/blog/app/templates/admin/base.html` - Accurate

### Override Files
- `/Users/davidbowman/projects/blog/app/static/AGENTS.override.md` - Missing critical.css
- `/Users/davidbowman/projects/blog/app/templates/AGENTS.override.md` - Outdated structure
