# Frontend Module Architecture Review

**Review Date:** 2026-05-09
**Reviewer:** frontend_reviewer
**Module:** Frontend (app/static/ and app/templates/)

---

## Verified Accurate Claims

The following claims in the documentation are **confirmed accurate** by cross-referencing with actual source code:

### Templates Documentation (templates.md)
1. **Template filters verified** (app/filters.py):
   - `markdown_safe` - Render markdown to HTML with nh3 sanitization (lines 12-17)
   - `reading_time` - Calculate reading time from text content (lines 19-25)
   - `sanitize_css` - Sanitize custom CSS input (lines 27-31)
   - `post_image_url` - Get post image URL with request-level caching (lines 33-50)
   - `post_image_srcset` - Generate srcset for responsive images (lines 52-73)

2. **Context processors verified** (app/context_processors.py):
   - `inject_csrf()` - Injects `csrf_token` and `csp_nonce` (lines 138-148)
   - `inject_config()` - Site config variables (lines 150-161)
   - `inject_theme()` - Theme settings and `custom_css` variable (lines 163-165)
   - `inject_footer_data()` - Footer links and data (lines 167-191)
   - `inject_show_footer_posts()` - `show_footer_posts` boolean (lines 193-200)

3. **Template inheritance structure** - base.html is foundation for both public and admin templates.

### Static Assets Documentation (static-assets.md)
1. **Directory structure** - Correctly identifies js/, css/, uploads/, dist/ directories.

2. **Vite Configuration** - Located at vite.config.js with JS bundling, SCSS/CSS processing, and asset optimization.

3. **CSS organization** - Base styles, component styles, and theme-specific styles.

### Overview Documentation (overview.md)
1. **Component locations** - All locations accurate: JavaScript (app/static/js/), CSS (app/static/css/), Uploads (app/static/uploads/), Vite Build (app/static/dist/), Templates (app/templates/).

---

## Inaccurate/Outdated Claims

### 1. templates.md - Missing `post_image_avif_url` Filter

**Claim:** Filters listed are: `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`

**Reality:** The `post_image_avif_url` filter exists (app/filters.py:75-83) and is documented in AGENTS.md (line 116: "post_image_avif_url filter added").

**Correction:** Add `post_image_avif_url` to the filters list.

### 2. templates.md - Incorrect Context Processor Variable Names

**Claim:** States `inject_config()` provides `site_name` and `site_tagline` variables.

**Reality:** The actual context processor injects: `site_title`, `site_description`, `author_name`, `author_role`, `author_avatar`, `base_url`, `current_year`, `canonical_url`. There is no `site_name` or `site_tagline`.

**Correction:** Update documentation to reflect actual injected variables.

### 3. static-assets.md - Vite Build Output Location

**Claim:** Vite build output is in `app/static/dist/`

**Reality:** This is accurate - vite.config.js specifies `outDir: 'dist'` relative to root (app/static/), so output is indeed at `app/static/dist/`.

### 4. AGENTS.override.md - Inconsistent Filter List

**Claim:** The AGENTS.override.md lists only 5 filters (lines 43-50) without `post_image_avif_url`.

**Reality:** Filters.py defines 6 filters including `post_image_avif_url`.

---

## Missing Documentation

### 1. CSS Architecture Details
- No documentation of the CSS file aggregation (style.css aggregates all CSS files)
- Dark mode as default with `data-theme` attribute for light mode toggle
- No mention of `critical.css` for above-the-fold rendering
- Font family self-hosting (Inter, JetBrains Mono) and `@font-face` declarations

### 2. JavaScript Module System
- Missing documentation on the `export default initXxx` requirement for JS modules
- Missing documentation on `import.meta.glob()` for dynamic route-based module loading
- Mobile menu is created dynamically in JavaScript (not in HTML templates)
- Admin page detection via `document.body.classList.contains('admin-body')`

### 3. Vite Asset Helper Function
- No documentation of `vite_asset()` helper in `app/vite.py`
- Content hashing behavior for JS vs CSS assets
- Manifest file location and usage

### 4. Lazy Image Progressive Enhancement
- CSS pattern for lazy loading: `opacity: 0` default with `.loaded` class
- JavaScript adds `document.documentElement.classList.add('js')` first

### 5. GPU Acceleration for Blur Effects
- `will-change: backdrop-filter` requirement for navbar, nav-links, modal-overlay

### 6. Template Caching Recommendations
- AGENTS.override.md mentions caching filter results in loops, but main docs don't cover this

### 7. Prism.js Syntax Highlighting Themes
- Available themes: prism (default), prism-coy, prism-dark, prism-funky, prism-okaidia, prism-tomorrow
- Theme selection via `SiteSettings.syntax_theme`

### 8. Assets Policy
- No external assets - all fonts self-hosted
- Prism.js is self-hosted with extended language definitions

---

## Potential Issues

### 1. CSS style.css Import Pattern
The AGENTS.override.md mentions `style.css` aggregates all CSS files, but:
- No `style.css` file exists in app/static/css/ (based on glob results)
- The build system likely generates this, but documentation doesn't clarify

### 2. Vite Configuration Inconsistency
The vite.config.js specifies manualChunks for vendor, admin, and public only, but dist/ contains many more chunks (upload, dark-mode, filter-select, share, utils, code-copy, toc, anchor-links, prefetch, nav-dropdown, media-copy, bulk, lazy-load, toast, lightbox, editor, shortcuts, modal). This suggests manualChunks is incomplete or outdated.

### 3. Template Directory Discrepancies
The templates.md shows a simplified directory structure, but actual templates include many more files than documented.

### 4. public/ Subdirectory Confusion
The AGENTS.override.md shows `public/` subdirectory for templates, but actual public templates are flat (no public/ subdirectory inside templates/).

### 5. Email Templates Scope
templates.md shows email/ directory but doesn't mention base_email.html.

---

## Recommended Improvements

### Priority 1: Fix Inaccuracies

1. **Update templates.md filter list** to include `post_image_avif_url`
2. **Correct inject_config() variable names** - change `site_name` to `site_title`, `site_tagline` to `site_description`
3. **Update AGENTS.override.md** filter list to match actual filters

### Priority 2: Add Missing Documentation

1. **Add CSS architecture section** covering:
   - File structure and aggregation
   - Dark mode implementation
   - Self-hosted fonts policy
   - GPU acceleration patterns

2. **Add JavaScript module initialization section** with:
   - `export default initXxx` requirement
   - `import.meta.glob()` pattern for dynamic imports
   - Mobile menu JS creation
   - Admin body class detection

3. **Document Vite asset handling**:
   - `vite_asset()` helper usage
   - Content hashing differences for JS vs CSS
   - Manifest file location

4. **Add responsive images documentation**:
   - Width variants (400w, 800w, 1200w)
   - srcset usage pattern

### Priority 3: Improve Clarity

1. **Unify directory structure diagrams** - ensure all docs show actual template locations
2. **Add cross-references** between related docs (e.g., filters <> context processors)
3. **Document the actual chunk split strategy** or update vite.config.js to match documented behavior

---

## Summary

The frontend documentation has a solid foundation but requires updates:

- **Verified accurate:** Core filter and context processor names, directory structure, Vite configuration location
- **Needs fixing:** Filter list is missing `post_image_avif_url`, context processor variable names don't match actual implementation
- **Missing coverage:** JS module system, CSS architecture, Vite asset helpers, lazy loading patterns, syntax highlighting themes
- **Potential bugs:** None identified - implementation appears consistent
- **Security:** No issues found - CSS sanitization is properly implemented

The AGENTS.override.md files in app/static/ and app/templates/ are more comprehensive and accurate than the architecture docs in architecture/frontend/. The architecture docs should be updated to reflect the more detailed information in the AGENTS override files.
