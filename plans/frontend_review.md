# Frontend Architecture Review

**Date:** May 6, 2026  
**Reviewer:** Architecture Review Agent  
**Documents Reviewed:**
- `/home/sugarwookie/projects/blog/architecture/frontend/templates.md`
- `/home/sugarwookie/projects/blog/architecture/frontend/static-assets.md`
- `/home/sugarwookie/projects/blog/architecture/frontend/overview.md`
- `/home/sugarwookie/projects/blog/app/templates/AGENTS.override.md`
- `/home/sugarwookie/projects/blog/app/static/AGENTS.override.md`

---

## Summary

The architecture documents for the frontend contain several inaccuracies, missing filters, incorrect context processor names, and one missing CSS file. The most critical issues are:

1. **Critical Bug**: `critical.css` is referenced in `base.html` (line 22) but does not exist
2. **Missing Filters**: `format_date`, `markdown`, `slugify` documented but do not exist
3. **Wrong Context Names**: `site_settings`, `tag_cache`, `footer_data` documented but don't match implementation
4. **Missing Directory**: `app/static/css/styles/` documented but does not exist

The AGENTS override files have additional inaccuracies regarding filter definitions.

---

## Verified Claims

### Correct Claims from overview.md

| Claim | Location | Status |
|-------|----------|--------|
| JavaScript location | `app/static/js/` | VERIFIED |
| CSS location | `app/static/css/` | VERIFIED |
| Uploads location | `app/static/uploads/` | VERIFIED |
| Vite build output | `app/static/dist/` | VERIFIED |
| Templates location | `app/templates/` | VERIFIED |

### Correct Claims from static-assets.md

| Claim | Location | Status |
|-------|----------|--------|
| JS directory structure (js/admin, js/public, js/shared) | `app/static/js/` | VERIFIED |
| Vite config location | `vite.config.js` (project root) | VERIFIED |
| Uploads directory | `app/static/uploads/` | VERIFIED |

### Correct Claims from templates.md

| Claim | Location | Status |
|-------|----------|--------|
| Template inheritance: public templates extend base.html | `app/templates/` | VERIFIED |
| Template inheritance: admin templates extend base.html | `app/templates/admin/base.html` | VERIFIED |

---

## Discrepancies Found

### 1. MISSING CSS FILE: `critical.css` (BUG - HIGH Priority)

**Document:** `templates.md` references CSS structure, `base.html` line 22 references file

**Issue:** `critical.css` is referenced in `base.html:22` but does not exist in `app/static/css/`

```html
<!-- base.html:22 -->
<link rel="stylesheet" href="{{ vite_asset('css/critical.css') }}" media="screen">
```

**Actual files in `app/static/css/`:**
- admin.css, base.css, forms.css, layout.css, prism-*.css, public.css, utilities.css

**No `critical.css` exists.**

**Fix:** Either create `app/static/css/critical.css` or remove the reference from `base.html`

---

### 2. WRONG CSS DIRECTORY STRUCTURE (MEDIUM Priority)

**Document:** `static-assets.md` line 14
```markdown
├── css/
│   └── styles/         # SCSS/CSS files
```

**Issue:** `app/static/css/styles/` does not exist. CSS files are directly in `app/static/css/`

**Actual structure:**
```
app/static/css/
├── admin.css
├── base.css
├── forms.css
├── layout.css
├── prism-*.css (7 themes)
├── public.css
└── utilities.css
```

---

### 3. MISSING/INCORRECT FILTERS (BUG - HIGH Priority)

**Document:** `templates.md` lines 37-42
```markdown
## Filters

Registered in `app/filters.py`:
- `{{ post.date | format_date }}`
- `{{ post.body | markdown }}`
- `{{ tag.name | slugify }}`
```

**Issue:** These filters do not exist in `app/filters.py`

**Actual filters in `app/filters.py` (lines 11-72):**
- `markdown_safe` - Renders markdown with nh3 sanitization
- `reading_time` - Calculates reading time
- `sanitize_css` - Sanitizes CSS
- `post_image_url` - Gets post image URL with caching
- `post_image_srcset` - Generates responsive image srcset

**Verification:**
```bash
$ grep -r "format_date" app/templates/  # No matches
$ grep -r "slugify" app/templates/       # No matches
$ grep -r "markdown" app/templates/     # Uses markdown_safe
```

**Also in `app/templates/AGENTS.override.md` lines 44-50:**
```markdown
## Template Filters

Defined in `app/filters.py`:
- `truncate` - Truncate text with ellipsis
- `markdown_safe` - Render markdown to HTML
- `custom_css` - Apply custom CSS theme
```

**Issues:**
- `truncate` is Jinja2's built-in filter, NOT defined in `app/filters.py`
- `custom_css` is NOT a filter - it's a context variable sanitized with `sanitize_css`

---

### 4. WRONG CONTEXT PROCESSOR NAMES (BUG - MEDIUM Priority)

**Document:** `templates.md` lines 43-48
```markdown
## Context Processors

From `app/context_processors.py`:
- `site_settings` - Theme and settings
- `tag_cache` - Cached tag counts
- `footer_data` - Footer links
```

**Issue:** These variable names do not exist in templates

**Actual context processors in `app/context_processors.py`:**

1. **`inject_csrf()`** (line 138-148) - provides `csrf_token`, `csp_nonce`

2. **`inject_config()`** (line 150-161) - provides:
   - `site_title`, `site_description`, `author_name`, `author_role`, `author_avatar`, `base_url`, `current_year`, `canonical_url`

3. **`inject_theme()`** (line 163-165) - provides `theme` (which contains theme_preset, theme_vars, syntax_theme, custom_css_enabled, custom_css, logo_text, theme_presets)

4. **`inject_footer_data()`** (line 167-191) - provides:
   - `recent_posts_footer`, `recent_posts_sidebar`, `footer_tags`, `footer_tag_counts`

5. **`inject_show_footer_posts()`** (line 193-200) - provides `show_footer_posts`

**`tag_cache`** is NOT a context processor - it's a separate module at `app/tag_cache.py` providing `_get_tag_counts()` function

**`footer_data`** is not a single variable - footer data is split into multiple variables

---

### 5. INCOMPLETE TEMPLATE DIRECTORY STRUCTURE (MEDIUM Priority)

**Document:** `templates.md` lines 7-26

**Issue:** Many templates are missing from the documented structure

**Missing templates that exist:**
- `archive.html` - Full post archive
- `series.html` - Public series view
- `macros.html` - Jinja macros (pagination, etc.)
- `_sidebar.html` - Sidebar partial
- `_post_content.html` - Post content partial
- `_error.html` - Error page partial
- `public_preview.html` - Preview page
- `page.html` - Static page view
- `429.html` - Rate limit page

**Missing admin templates that exist:**
- `2fa_setup.html`, `2fa_verify.html`, `login_2fa.html` - 2FA
- `revision_diff.html`, `revisions.html` - Post revisions
- `audit.html` - Audit log
- `series.html`, `series_editor.html`, `series_posts.html` - Series management
- `login_base.html` - Login base
- `forgot-password.html`, `reset-password.html` - Password reset
- `analytics.html` - Analytics
- `comments.html` - Comment management

**Missing email templates that exist:**
- `base_email.html` - Base email template

---

### 6. ADMIN JS FEATURE MISMAPPING (LOW Priority)

**Document:** `static-assets.md` lines 21-25
```markdown
### Admin JS
- Dashboard functionality
- Post editor enhancements
- Media management
- Settings forms
```

**Issue:** "Media management" suggests an admin/media.js file, but actual JS files are:
- `app/static/js/admin/bulk.js` - Bulk actions
- `app/static/js/admin/editor.js` - Post editor
- `app/static/js/admin/shortcuts.js` - Keyboard shortcuts

Media management uses `app/static/js/upload.js` at the root level, not in admin/

---

### 7. PUBLIC JS COMMENTS CLAIM (LOW Priority)

**Document:** `static-assets.md` lines 27-31
```markdown
### Public JS
- Comments submission
- Newsletter subscription
- Search functionality
```

**Issue:** "Comments submission" suggests a public/comments.js file

**Actual:** Comments are handled via Jinja2 macros in `app/templates/public/comments.html` - no JavaScript involved for basic comment submission

---

## Bugs Identified

### BUG-1: Missing critical.css (HIGH)
- **Location:** `app/templates/base.html:22`
- **Issue:** References non-existent `critical.css`
- **Impact:** 404 error for this stylesheet request
- **Fix:** Create `app/static/css/critical.css` with critical CSS, or remove the reference

### BUG-2: Non-existent filters documented (HIGH)
- **Location:** `architecture/frontend/templates.md:37-42`
- **Issue:** `format_date`, `markdown`, `slugify` filters don't exist
- **Impact:** Developers expecting these filters will be confused
- **Fix:** Update documentation to reflect actual filters

### BUG-3: AGENTS.override.md documents non-existent filters (MEDIUM)
- **Location:** `app/templates/AGENTS.override.md:44-50`
- **Issue:** Lists `truncate` and `custom_css` as filters in `app/filters.py`
- **Impact:** Developers may try to use these as filters
- **Fix:** Remove `truncate` (it's Jinja2 built-in) and `custom_css` (it's a context variable)

---

## Improvement Recommendations

### IMP-1: Create critical.css (HIGH Priority)
**File:** `app/static/css/critical.css`

Create a critical CSS file for above-the-fold content to improve page load performance. This is referenced in `base.html:22` but doesn't exist.

---

### IMP-2: Update templates.md Filters Section (HIGH Priority)
**File:** `architecture/frontend/templates.md:37-42`

**Current (WRONG):**
```markdown
## Filters

Registered in `app/filters.py`:
- `{{ post.date | format_date }}`
- `{{ post.body | markdown }}`
- `{{ tag.name | slugify }}`
```

**Proposed:**
```markdown
## Filters

Registered in `app/filters.py`:
- `{{ post.body | markdown_safe }}` - Render markdown to HTML with sanitization
- `{{ post.body | reading_time }}` - Calculate reading time (e.g., "5 min read")
- `{{ css | sanitize_css }}` - Sanitize custom CSS
- `{{ post | post_image_url }}` - Get post image URL with caching
- `{{ post | post_image_srcset }}` - Generate responsive srcset

Note: Jinja2 built-in filters like `truncate`, `format`, `length` are also available.
```

---

### IMP-3: Update templates.md Context Processors Section (MEDIUM Priority)
**File:** `architecture/frontend/templates.md:43-48`

**Current (WRONG):**
```markdown
## Context Processors

From `app/context_processors.py`:
- `site_settings` - Theme and settings
- `tag_cache` - Cached tag counts
- `footer_data` - Footer links
```

**Proposed:**
```markdown
## Context Processors

From `app/context_processors.py`:

- **Theme (`theme`)** - Theme settings via `inject_theme()`:
  - `theme_preset`, `theme_vars`, `syntax_theme`, `custom_css_enabled`, `custom_css`, `logo_text`, `theme_presets`

- **Config (`site_title`, `site_description`, etc.)** - Site configuration via `inject_config()`:
  - `site_title`, `site_description`, `author_name`, `author_role`, `author_avatar`, `base_url`, `current_year`, `canonical_url`

- **Footer (`recent_posts_footer`, `footer_tags`, etc.)** - Footer data via `inject_footer_data()`:
  - `recent_posts_footer`, `recent_posts_sidebar`, `footer_tags`, `footer_tag_counts`, `show_footer_posts`

- **CSRF (`csrf_token`, `csp_nonce`)** - Security tokens via `inject_csrf()`

Note: `tag_cache` is a separate module (`app/tag_cache.py`), not a context processor.
```

---

### IMP-4: Fix templates.md Directory Structure (MEDIUM Priority)
**File:** `architecture/frontend/templates.md:5-26`

Update to reflect actual template structure with all existing templates listed.

---

### IMP-5: Fix static-assets.md CSS Directory (MEDIUM Priority)
**File:** `architecture/frontend/static-assets.md:13-14`

**Current:**
```markdown
├── css/
│   └── styles/         # SCSS/CSS files
```

**Proposed:**
```markdown
├── css/                # CSS files (directly in this directory)
```

---

### IMP-6: Update AGENTS.override.md Filters Section (MEDIUM Priority)
**File:** `app/templates/AGENTS.override.md:44-50`

**Current:**
```markdown
## Template Filters

Defined in `app/filters.py`:
- `reading_time` - Calculate reading time from HTML content
- `post_image_url` - Get post image URL with request-level caching
- `post_image_srcset` - Generate srcset for responsive images
- `truncate` - Truncate text with ellipsis
- `markdown_safe` - Render markdown to HTML (uses nh3 for sanitization)
- `custom_css` - Apply custom CSS theme
```

**Proposed:**
```markdown
## Template Filters

Defined in `app/filters.py` (lines 11-72):
- `markdown_safe` - Render markdown to HTML with nh3 sanitization
- `reading_time` - Calculate reading time from text content
- `sanitize_css` - Sanitize custom CSS input
- `post_image_url` - Get post image URL with request-level caching
- `post_image_srcset` - Generate srcset for responsive images

Note: Jinja2 built-in filters like `truncate`, `format`, `length` are also available.
Note: `custom_css` is a context variable (from `inject_theme()`), not a filter.
```

---

### IMP-7: Add Vite Code Splitting Documentation (MEDIUM Priority)
**File:** `architecture/frontend/static-assets.md`

The Vite build system uses dynamic imports for code splitting. Add documentation about:
- Route-based code splitting in `main.js`
- Admin modules: bulk.js, editor.js, shortcuts.js
- Public modules: share.js, lightbox.js, toc.js, search.js, etc.
- Upload module: upload.js

---

## Priority Summary

| Item | Priority | Type |
|------|----------|------|
| Create missing critical.css | HIGH | Bug Fix |
| Document non-existent filters | HIGH | Documentation |
| AGENTS.override.md filter list | MEDIUM | Documentation |
| Context processor names | MEDIUM | Documentation |
| Template directory structure | MEDIUM | Documentation |
| CSS directory structure | MEDIUM | Documentation |
| Admin/public JS claims | LOW | Documentation |
| Vite code splitting docs | MEDIUM | Improvement |

---

## Files Referenced

### Templates
- `app/templates/base.html` - Line 22 (critical.css reference)
- `app/templates/index.html` - Line 23 (reading_time filter usage)
- `app/templates/post.html` - Lines 3, 4 (truncate, post_image_url, post_image_srcset)

### Filters & Context
- `app/filters.py` - Lines 11-72 (actual filter definitions)
- `app/context_processors.py` - Lines 138-200 (actual context processors)
- `app/tag_cache.py` - (NOT a context processor, separate module)

### Static Assets
- `app/static/css/` - CSS files (no styles/ subdirectory)
- `app/static/js/admin/` - bulk.js, editor.js, shortcuts.js
- `app/static/js/upload.js` - Media upload (not in admin/)
- `app/static/dist/.vite/manifest.json` - Vite build manifest

### Vite
- `vite.config.js` - Project root
- `app/vite.py` - vite_asset() function (lines 47-77)
