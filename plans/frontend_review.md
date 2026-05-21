# Frontend Architecture Review

## Summary

Reviewed architecture documents in `architecture/frontend/` against actual implementation in `app/static/` and `app/templates/`. The documentation is mostly accurate but several discrepancies and one critical bug were identified.

---

## Verified Claims

### Directory Structure (static-assets.md)
- **Correct**: `app/static/js/` contains `admin/`, `public/`, `shared/`, `lib/` subdirectories
- **Correct**: Admin JS files: `bulk.js`, `editor.js`, `shortcuts.js`
- **Correct**: Public JS files: `anchor-links.js`, `code-copy.js`, `lightbox.js`, `media-copy.js`, `search.js`, `share.js`, `toc.js`
- **Correct**: Shared JS files: `dark-mode.js`, `filter-select.js`, `lazy-load.js`, `modal.js`, `nav-dropdown.js`, `prefetch.js`, `toast.js`, `utils.js`
- **Correct**: JSX file `mobile-menu.jsx` exists in `app/static/js/shared/`

### JavaScript Module Pattern (static-assets.md:49-59)
- **Correct**: All modules export default initialization functions following `initXxx` naming convention:
  - `initDarkMode`, `initToast`, `initSearch`, `initShare`, `initUpload`, `initEditor`, `initMobileMenu`, `initLazyLoad`, `initNavDropdown`, `initSharedUtils`, `initImagePreview`, `initPrefetch`
- **Correct**: `main.js:85-96` calls `module.default()` if it exists

### Route-Based Code Splitting (static-assets.md:61-77)
- **Correct**: `main.js:30-83` implements `ROUTE_MODULES` with routes: `/admin/posts`, `/admin/media`, `/admin/`
- **Correct**: `getModulesForPath()` returns route-specific modules or default public modules

### JSX Support (static-assets.md:90-103)
- **Correct**: `vite.config.js:31-39` has `esbuildOptions` with `.jsx` loader configuration
- **Correct**: `mobile-menu.jsx` is the only JSX file in the project

### Vite Configuration (static-assets.md:124-130)
- **Correct**: Entry point is `app/static/js/main.js` (vite.config.js:12)
- **Correct**: Output is `app/static/dist/` (vite.config.js:7)
- **Correct**: `manualChunks` creates vendor, admin, public chunks (vite.config.js:15-19)
- **Correct**: Dev server runs on port 3000 with proxy to Flask on 5000 (vite.config.js:24-28)

### Filters (templates.md:75-83)
- **Correct**: All filters registered in `app/filters.py`:
  - `markdown_safe` (line 12-17)
  - `reading_time` (line 19-25)
  - `sanitize_css` (line 27-31)
  - `post_image_url` (line 33-50)
  - `post_image_srcset` (line 52-73)
  - `post_image_avif_url_stub` (line 75-85)

### Context Processors (templates.md:85-96)
- **Correct**: All context processors in `app/context_processors.py`:
  - `inject_csrf()` (line 138-148)
  - `inject_config()` (line 150-161)
  - `inject_theme()` (line 163-165)
  - `inject_footer_data()` (line 167-191)
  - `inject_show_footer_posts()` (line 193-199)

### Cache Invalidation Functions (templates.md:98-102)
- **Correct**: `invalidate_settings_cache()` at context_processors.py:30-32
- **Correct**: `invalidate_footer_cache()` at context_processors.py:35-37

---

## Discrepancies

### 1. `prism.min.js` location (static-assets.md:35)
**Documentation says**: `lib/` contains `marked-wrapper.js`, `marked.min.js`, `prism.min.js`
**Actual location**: `prism.min.js` is at `app/static/js/prism.min.js` (root of js/)
**Severity**: Medium - minor inaccuracy, doesn't affect functionality since lib only has marked files

### 2. Template `_breadcrumbs.html` (templates.md:9)
**Documentation says**: `app/templates/_breadcrumbs.html` exists
**Actual location**: Only `app/templates/admin/_breadcrumbs.html` exists
**Severity**: Low - documentation error, no runtime impact

### 3. Admin template listing (templates.md:27)
**Documentation lists**: `admin/series.html`, `admin/series_editor.html`, `admin/series_posts.html`
**Actual files exist**: Yes, all three exist and match
**Note**: The template list is incomplete (missing `admin/tags.html`, `admin/comments.html`, etc.) but the key ones are present

---

## Bugs Identified

### Critical: Syntax Error in `mobile-menu.jsx` (app/static/js/shared/mobile-menu.jsx:42)

```javascript
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const hamburger = document.querySelector('.mobile-menu-toggle');
                const nav = document.querySelector('.nav-links');
                if (hamburger && nav) {
                    hamburger.setAttribute('aria-expanded', 'false');
                    nav.classList.remove('open');
                }
});
    });
}
```

Line 42 has `});` which doesn't match any opening bracket. The correct structure should be:
```javascript
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const hamburger = document.querySelector('.mobile-menu-toggle');
                const nav = document.querySelector('.nav-links');
                if (hamburger && nav) {
                    hamburger.setAttribute('aria-expanded', 'false');
                    nav.classList.remove('open');
                }
            }
        });
    });
}
```

**Impact**: The module will fail to parse when Vite/ESBuild tries to bundle it. The `initMobileMenu` function is never executed because the syntax error prevents the file from loading.

**Fix**: Remove the extra `});` at line 42, change to:
```javascript
            }
        });
    });
}
```

### High: Undefined `srcset` variable in search.html (app/templates/search.html:31)

```html
<img src="{{ url_for('static', filename='uploads/' + img) }}" srcset="{{ srcset }}" ...>
```

The `srcset` variable is used but never defined in this template. It should be:
```html
{% set srcset = post | post_image_srcset %}
<img src="{{ url_for('static', filename='uploads/' + img) }}" srcset="{{ srcset if srcset else '' }}" ...>
```

**Impact**: Images in search results never render with responsive srcset, causing potential layout issues or missing images.

---

## Improvement Recommendations

### 1. Fix `mobile-menu.jsx` Syntax Error (Critical - Immediate)

**File**: `app/static/js/shared/mobile-menu.jsx`

**Change lines 39-43 from:**
```javascript
        if (hamburger && nav) {
            hamburger.setAttribute('aria-expanded', 'false');
            nav.classList.remove('open');
        }
});
    });
}
```

**To:**
```javascript
        if (hamburger && nav) {
            hamburger.setAttribute('aria-expanded', 'false');
            nav.classList.remove('open');
            }
        });
    });
}
```

Or better yet, properly format:
```javascript
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const hamburger = document.querySelector('.mobile-menu-toggle');
                const nav = document.querySelector('.nav-links');
                if (hamburger && nav) {
                    hamburger.setAttribute('aria-expanded', 'false');
                    nav.classList.remove('open');
                }
            }
        });
    });
}
```

### 2. Fix `srcset` undefined in search.html (High)

**File**: `app/templates/search.html`

**After line 25** (`{% for post in posts %}`), add:
```jinja2
{% set srcset = post | post_image_srcset %}
```

Or fix line 31 to handle the undefined case:
```html
<img src="{{ url_for('static', filename='uploads/' + img) }}" srcset="{{ srcset | default('') }}" ...>
```

Actually, since `post_image_srcset` returns `None` when there's no image or caching context, the variable needs to be set before the img tag.

### 3. Update static-assets.md `lib/` listing

**File**: `architecture/frontend/static-assets.md:32-35`

**Change from:**
```markdown
│   ├── lib/            # Third-party libraries
│   │   ├── marked-wrapper.js
│   │   ├── marked.min.js
│   │   └── prism.min.js
```

**To:**
```markdown
│   ├── lib/            # Third-party libraries
│   │   ├── marked-wrapper.js
│   │   └── marked.min.js
│   ├── prism.min.js     # Syntax highlighter (root level for manualChunks)
```

### 4. Add missing template `_breadcrumbs.html` or update docs

**Option A**: Create `app/templates/_breadcrumbs.html` as a generic version used by public templates
**Option B**: Update `architecture/frontend/templates.md` to note only `admin/_breadcrumbs.html` exists

### 5. Documentation: Add missing CSS files to static-assets.md

The docs list CSS in `app/static/css/` but don't enumerate all files. The actual files are:
- `admin.css`
- `base.css`
- `critical.css`
- `forms.css`
- `layout.css`
- `prism-coy.css`
- `prism-dark.css`
- `prism-funky.css`
- `prism-okaidia.css`
- `prism-tomorrow.css`
- `prism.css`
- `public.css`
- `utilities.css`

### 6. Consider adding Lazy Load module to public default modules

**File**: `app/static/js/main.js:68-82`

Currently the default route doesn't include `lazy-load.js`:
```javascript
return [
    './shared/utils.js',
    './shared/toast.js',
    './shared/dark-mode.js',
    './shared/mobile-menu.jsx',  // has bug
    './shared/lazy-load.js',
    './shared/prefetch.js',
    './public/share.js',
    './public/lightbox.js',
    './public/toc.js',
    './public/code-copy.js',
    './public/anchor-links.js',
    './public/media-copy.js',
    './public/search.js',
];
```

`lazy-load.js` IS included in the default modules (line 73). This is correct but note that `mobile-menu.jsx` will fail due to syntax error.

---

## Priority Summary

| Priority | Issue | Location | Status |
|----------|-------|----------|--------|
| Critical | Syntax error in mobile-menu.jsx | app/static/js/shared/mobile-menu.jsx:42 | Needs fix |
| High | Undefined `srcset` variable | app/templates/search.html:31 | Needs fix |
| Medium | prism.min.js location inaccuracy | architecture/frontend/static-assets.md:35 | Doc fix |
| Low | _breadcrumbs.html in root templates | architecture/frontend/templates.md:9 | Doc fix |

---

## Testing Recommendations

1. **Test mobile menu on mobile viewport** - will fail due to syntax error
2. **Test search results with images** - srcset may be undefined
3. **Verify lazy loading works** - should be functional if syntax error in mobile-menu doesn't break entire module loading chain