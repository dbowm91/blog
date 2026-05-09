# Frontend Architecture Review

Reviewed: `architecture/frontend/`, `app/static/AGENTS.override.md`
Verified against: `app/filters.py`, `app/context_processors.py`, `app/vite.py`, `app/static/js/main.js`, templates

---

## Verified Claims

### Template Filters (`app/filters.py:11-73`)
All documented filters exist and match implementation:
- `markdown_safe` (line 12)
- `reading_time` (line 19)
- `sanitize_css` (line 27)
- `post_image_url` (line 33)
- `post_image_srcset` (line 52)
- `post_image_avif_url` (line 75) - bonus stub for AVIF support

### Context Processors (`app/context_processors.py:135-200`)
All documented context processors exist and match implementation:
- `inject_csrf()` (line 139) - injects `csrf_token` and `csp_nonce`
- `inject_config()` (line 151) - injects site config variables
- `inject_theme()` (line 164) - injects theme settings and `custom_css`
- `inject_footer_data()` (line 168) - injects footer links and data
- `inject_show_footer_posts()` (line 194) - injects `show_footer_posts` boolean

### Directory Structure (`app/static/AGENTS.override.md:6-28`)
Matches actual structure with one exception:
- `mobile-menu.jsx` exists (JSX, not .js) - verified at `app/static/js/shared/mobile-menu.jsx:45`

### JS Module Export Pattern (`app/static/AGENTS.override.md:55-57`)
Verified: All 21 JS modules correctly export `export default initXxx;`

### Vite Configuration (`app/static/AGENTS.override.md:30-54`)
- Content hashing implemented via `app/vite.py:47-77`
- Manifest lookup for JS (line 67-69), MD5 hash for CSS (line 72-74)
- `vite_asset()` helper registered in Jinja (line 81)

### Route-Based Code Splitting (`app/static/AGENTS.override.md:61-63`)
Matches `app/static/js/main.js:30-83` - admin pages get admin modules, public pages get public modules.

### Mobile Menu Dynamically Created (`app/static/AGENTS.override.md:65-67`)
Verified: `mobile-menu.jsx:1-43` creates hamburger button dynamically via `document.createElement('button')`.

### Syntax Highlighting Themes (`app/static/AGENTS.override.md:96-100`)
CSS files exist for all 6 themes: prism.css, prism-coy.css, prism-dark.css, prism-funky.css, prism-okaidia.css, prism-tomorrow.css

### Responsive Images (`app/static/AGENTS.override.md:77-79`)
`post_image_srcset` filter at `app/filters.py:52-73` generates srcset at 400w, 800w, 1200w.

---

## Discrepancies

### 1. `mobile-menu.jsx` is JSX, not `.js`
**Impact**: Low - Vite handles JSX via esbuildOptions (vite.config.js:34)
**Reference**: `app/static/js/shared/mobile-menu.jsx`

### 2. Vite manualChunks don't match route-based splitting
**Document says**: "Admin pages get utils, modal, shortcuts, bulk. Public pages get utils, dark-mode, mobile-menu, lazy-load, share, lightbox, toc."
**Actual (vite.config.js:15-19)**:
```javascript
manualChunks: {
  'vendor': ['prism.min.js', 'prism-languages.js'],
  'admin': resolve(__dirname, 'app/static/js/admin/editor.js'),
  'public': resolve(__dirname, 'app/static/js/public/search.js'),
}
```
Only `editor.js` and `search.js` have explicit chunks; other splitting happens via `main.js:30-83` dynamic imports.

### 3. Templates.md incomplete directory listing
**Document shows**: `admin/`, `email/`, `public/` subdirectories with few files
**Actual**: 50+ template files including `admin/backup_codes.html`, `admin/disable_2fa.html`, `admin/comments.html`, `admin/series*.html`, etc.

### 4. Static-assets.md incomplete
**Document says** `app/static/uploads/` but only `app/static/img/` and `app/static/fonts/` exist in repository. Uploads may be stored elsewhere (S3, etc.).

---

## Bugs Found

### Bug 1: Prism Theme Loaded via Script Injection, Not Vite
**Location**: `app/static/js/main.js:97-112`
```javascript
function loadPrismIfNeeded() {
    const prismCSS = document.createElement('link');
    prismCSS.href = '/static/css/prism-okaidia.css';  // HARDCODED
    document.head.appendChild(prismCSS);
    const prismJS = document.createElement('script');
    prismJS.src = '/static/js/prism.min.js';  // NOT via vite_asset()
```
**Issue**: 
- Theme is hardcoded to `prism-okaidia.css` (line 102), ignoring `syntax_theme` setting
- JS files loaded directly from `/static/` bypassing `vite_asset()` - no content hashing
- No AVIF support detected (filter returns `None` at `app/filters.py:82`)

### Bug 2: `post_image_avif_url` Filter Always Returns None
**Location**: `app/filters.py:75-83`
```python
def post_image_avif_url_filter(post: Any) -> str | None:
    if not post or not post.image:
        return None
    return None  # Always None - stub implementation
```
**Issue**: AVIF encoding is planned but not implemented. The filter should indicate this or check for actual AVIF variants.

---

## Specific Improvements

### IMP-1: Fix Prism loading to respect syntax_theme
**File**: `app/static/js/main.js:97-112`
**Change**: Pass `syntax_theme` from template context and use `vite_asset()` for hashed filenames

### IMP-2: Document actual template file structure
**File**: `architecture/frontend/templates.md:6-26`
**Change**: Update directory tree to reflect all ~50 template files, or reference the actual glob

### IMP-3: Clarify uploads storage location
**File**: `architecture/frontend/static-assets.md:14`
**Change**: Note that uploads may be stored in cloud storage (S3, etc.) rather than `app/static/uploads/`

### IMP-4: Document route-based chunk strategy fully
**File**: `architecture/frontend/static-assets.md` or create `frontend/vite.md`
**Change**: Document that splitting is done in `main.js` via `import.meta.glob`, not just in `vite.config.js`

### IMP-5: Implement AVIF encoding or remove stub filter
**File**: `app/filters.py:75-83`
**Change**: Either implement actual AVIF variant lookup or rename filter to `post_image_avif_url_stub` to clarify its status

---

## Summary

| Area | Status |
|------|--------|
| Template filters | ✅ All correct |
| Context processors | ✅ All correct |
| JS module exports | ✅ All correct |
| Mobile menu dynamic creation | ✅ Correct |
| Directory structure | ⚠️ Minor (JSX vs JS) |
| Vite config vs docs | ⚠️ Chunk splitting different |
| Prism loading | ❌ Bug - hardcoded theme |
| AVIF filter | ❌ Bug - always returns None |

Priority: Fix Prism loading bug (IMP-1) as it affects user experience on code-heavy posts.