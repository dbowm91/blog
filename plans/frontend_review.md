# Frontend Architecture Review - Improvement Plan

## Overview

Reviewed `architecture/frontend/` documents against actual code in `app/static/` and `app/templates/`:
- `architecture/frontend/overview.md` (17 lines)
- `architecture/frontend/static-assets.md` (134 lines)
- `architecture/frontend/templates.md` (105 lines)

Cross-referenced with:
- `vite.config.js`
- `app/filters.py`
- `app/context_processors.py`
- `app/vite.py`
- Actual JS/CSS assets
- Built output in `app/static/dist/`

---

## Critical Bugs Found

### 1. Syntax Error in `mobile-menu.jsx` (CRITICAL)

**File**: `app/static/js/shared/mobile-menu.jsx:42`

```javascript
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                // ...
            }
        });
});  // <-- EXTRA closing - syntax error!
```

There is an extra `});` on line 42 after the closing brace of the `keydown` event listener. This prevents the JSX file from being compiled by Vite.

**Evidence**: No `mobile-menu*.js` file exists in `app/static/dist/` despite `mobile-menu.jsx` being in `main.js:18,72`.

**Fix**: Remove the extra `});` on line 42.

---

### 2. `marked-wrapper.js` is Non-Functional in Production

**File**: `app/static/js/lib/marked-wrapper.js:6-18`

```javascript
let markedCode = '';
fetch('./marked.min.js').then(r => r.text()).then(code => {
    markedCode = code;
}).catch(() => {
    markedCode = '';
});

function loadMarked() {
    const markedFn = new Function(markedCode + '; return marked;');
    return markedFn();
}
```

This implementation:
1. Uses `fetch()` to load `marked.min.js` at runtime
2. Uses `new Function()` to execute the loaded code
3. Will fail in production builds (fetch to relative path won't work)
4. Is used by `editor.js:2` for markdown preview

**Impact**: Markdown preview in the post editor will fail in production.

**Fix**: Replace with proper ES module import or bundler-friendly approach.

---

### 3. Vite Build Environment Broken

**Error**:
```
Error [ERR_MODULE_NOT_FOUND]: Cannot find module '/Users/davidbowman/projects/blog/node_modules/dist/node/cli.js'
```

Running `npm run build` fails due to corrupted node_modules. This means:
- Frontend assets cannot be rebuilt
- mobile-menu.jsx bug prevents proper compilation
- marked-wrapper.js issue cannot be auto-fixed via rebuild

**Fix**: Run `npm install` to restore node_modules.

---

## Documentation Discrepancies

### 4. `mobile-menu.jsx` Included in Routes But Not Compiled

**Documentation** (`static-assets.md:27`): JSX files handled via Vite esbuild options.

**Reality**:
- `mobile-menu.jsx` is imported in `main.js:18,72`
- No compiled output exists in `app/static/dist/`
- Syntax error prevents compilation

**Documentation Gap**: Should document that JSX files must have valid syntax before build.

---

### 5. Route Module Documentation Incomplete

**Documentation** (`static-assets.md:66-75`):
```javascript
const ROUTE_MODULES = {
    '/admin/posts': ['./shared/utils.js', './shared/modal.js', ...],
    '/admin/media': ['./shared/utils.js', './shared/modal.js', ...],
    '/admin/': ['./shared/utils.js', './shared/modal.js', ...],
};
```

**Reality**:
- Only `/admin/posts` and `/admin/media` include `image-preview.js`
- `/admin/` (dashboard) does NOT include `image-preview.js`
- Public modules are loaded via default route (lines 68-82), not specific routes
- `upload.js` appears in `/admin/media` route but is missing from dist output

**Documentation Gap**: Should clearly explain that public modules use a single default route.

---

### 6. Template Directory Structure Outdated

**Documentation** (`templates.md:5-64`) claims certain template files exist.

**Actual files** differ significantly:
- `admin/posts.html` - **DOES NOT EXIST** (actual is `admin/editor.html`)
- `admin/post_edit.html` - **DOES NOT EXIST** (actual is `admin/editor.html`)
- `admin/newsletter.html` - **DOES NOT EXIST** (newsletter is at `email/newsletter.html`)
- `public/subscribe.html` - **DOES NOT EXIST**

**Documentation Gap**: Several listed files don't exist; actual template names differ.

---

### 7. AGENTS.override.md Template Structure Also Outdated

**File**: `app/templates/AGENTS.override.md:15-40`

Same issues as `templates.md`:
- Lists `posts.html` but actual file is `editor.html`
- Lists `post_edit.html` which doesn't exist
- Lists `newsletter.html` as admin template (it's in `email/`)
- Lists `subscribe.html` which doesn't exist

---

### 8. CSS Directory Structure Incomplete

**Documentation** (`static-assets.md:118-122`):
```markdown
## CSS
Stylesheets in `app/static/css/`:
- Base styles
- Component styles
- Theme-specific styles
```

**Actual Files** (13 total):
- `admin.css`, `base.css`, `critical.css`, `forms.css`, `layout.css`
- `prism.css`, `prism-coy.css`, `prism-dark.css`, `prism-funky.css`, `prism-okaidia.css`, `prism-tomorrow.css`
- `public.css`, `utilities.css`

**Documentation Gap**: No documentation of actual CSS file purposes or organization.

---

### 9. Filter Documentation Missing `post_image_avif_url_stub` Behavior

**Documentation** (`templates.md:82`):
```markdown
- `post_image_avif_url_stub` - Returns None until AVIF encoding is enabled
```

**Actual Implementation** (`filters.py:75-84`):
```python
@app.template_filter("post_image_avif_url_stub")
def post_image_avif_url_filter(post: Any) -> str | None:
    """Return AVIF variant URL if available, else None.
    DEPRECATED: This filter is a stub and will always return None until
    AVIF encoding is properly implemented. It has been renamed to avoid
    confusion with a functional implementation.
    """
```

**Documentation Gap**: Should mark as deprecated and explain renaming.

---

### 10. Context Processor Cache Invalidation Functions Not Documented

**Documentation** (`templates.md:100-101`):
```markdown
- `invalidate_settings_cache()` - Invalidates the SiteSettings cache
- `invalidate_footer_cache()` - Invalidates the footer data memoization cache
```

**Reality**: These are `app/context_processors.py:30-37` but the documentation line numbers (30-32, 35-37) are now outdated.

**Documentation Gap**: Line numbers have changed; should reference functions not line numbers.

---

## Potential Improvements

### 11. Missing `vite_asset()` Documentation

The `vite_asset()` function in `app/vite.py:47-77` is used throughout templates (27 occurrences) but is not documented in `static-assets.md`.

**Documentation Gap**: Should document:
- Vite manifest lookup for JS files
- Content hash appending for CSS/other files
- CDN_URL support
- Jinja2 global usage

---

### 12. Public Module Route Loading Undocumented

**Documentation** (`static-assets.md:61-75`): Describes route-based splitting but doesn't explain default route fallback.

**Actual behavior** (`main.js:64-82`): Non-admin paths fall through to default module set:
```javascript
function getModulesForPath(path) {
    for (const [route, modules] of Object.entries(ROUTE_MODULES)) {
        if (path.startsWith(route)) return modules;
    }
    return [ /* all public modules */ ];
}
```

**Documentation Gap**: Default route behavior and module loading priority not explained.

---

### 13. Manual Chunks Configuration Misleading

**Documentation** (`static-assets.md:128`): "Code splitting via `manualChunks` (vendor, admin, public)"

**Actual Configuration** (`vite.config.js:15-19`):
```javascript
manualChunks: {
    'vendor': ['prism.min.js', 'prism-languages.js'],
    'admin': resolve(__dirname, 'app/static/js/admin/editor.js'),
    'public': resolve(__dirname, 'app/static/js/public/search.js'),
},
```

**Reality**: Only `admin` and `public` chunks are actually created; `vendor` chunk is defined but never generated as a separate file (prism files loaded via `<script>` tags directly).

**Documentation Gap**: vendor chunk doesn't actually exist in output.

---

### 14. Prism Language Loading Not Documented

**Documentation**: No mention of `prism-languages.js` or dynamic Prism loading.

**Actual behavior** (`main.js:97-112`): Prism is loaded lazily on demand:
```javascript
function loadPrismIfNeeded() {
    const codeBlocks = document.querySelectorAll('pre[class*="language-"]');
    if (codeBlocks.length === 0) return;
    // Dynamically load prism CSS, JS, and languages
}
```

**Documentation Gap**: Should document lazy Prism loading strategy.

---

### 15. Critical CSS Not Documented

**File**: `app/static/css/critical.css` (79 lines)

Contains above-the-fold styles for initial render but is not documented.

**Documentation Gap**: Should explain critical CSS purpose and loading pattern (loaded first, other CSS deferred via `media="print" onload="this.media='all'"`).

---

### 16. upload.js Missing from Build Output

**File**: `app/static/js/upload.js` is included in `main.js:16` and used in `/admin/media` route (`main.js:50`).

**Evidence**: No `upload*.js` in `app/static/dist/`.

**Likely Cause**: Vite build failed before generating it, or marked as external.

**Documentation Gap**: Should clarify if upload.js is intentionally excluded from bundling.

---

## Summary of Required Fixes

| # | Category | Issue | Severity |
|---|----------|-------|----------|
| 1 | Bug | Syntax error in mobile-menu.jsx | Critical |
| 2 | Bug | marked-wrapper.js non-functional in production | Critical |
| 3 | Env | Vite build broken (node_modules) | Critical |
| 4 | Docs | Template structure outdated | Medium |
| 5 | Docs | Route module behavior incomplete | Medium |
| 6 | Docs | CSS file organization undocumented | Low |
| 7 | Docs | post_image_avif_url_stub not marked deprecated | Low |
| 8 | Docs | vite_asset() function undocumented | Medium |
| 9 | Docs | Critical CSS not documented | Low |
| 10 | Docs | Prism lazy loading not documented | Low |

---

## Recommended Actions

1. **Immediate**:
   - Fix syntax error in `mobile-menu.jsx:42`
   - Fix or replace `marked-wrapper.js`
   - Run `npm install` to fix Vite build environment

2. **Documentation Updates**:
   - Update `templates.md` with actual template file names
   - Add section explaining route-based module loading with default fallback
   - Document `vite_asset()` function
   - Document critical CSS loading pattern
   - Mark `post_image_avif_url_stub` as deprecated

3. **Long-term**:
   - Consider converting `marked-wrapper.js` to proper ES module
   - Document CSS architecture and file purposes
   - Add section on Prism lazy loading strategy