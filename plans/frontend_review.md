# Frontend Module Architecture Review

**Review Date:** 2026-05-21
**Reviewer:** frontend_reviewer

---

## 1. Verified Accurate Claims

| Claim | Location | Evidence |
|-------|----------|----------|
| JS directory structure (admin/, public/, shared/, lib/) | `static-assets.md:7-39` | Verified - all directories exist at `app/static/js/` |
| CSS directory under `app/static/css/` | `static-assets.md:40` | Verified |
| Fonts directory under `app/static/fonts/` | `static-assets.md:41` | Verified |
| Uploads directory under `app/static/uploads/` | `static-assets.md:43` | Verified |
| Vite build output at `app/static/dist/` | `static-assets.md:44` | Verified |
| JSX support via esbuildOptions | `static-assets.md:92-103` | Verified - `vite.config.js:31-39` |
| prism.min.js location | `static-assets.md:35` | Verified - `app/static/js/prism.min.js` |
| prism-languages.js location | `static-assets.md:36` | Verified - `app/static/js/prism-languages.js` |
| mobile-menu.jsx exists in shared | `static-assets.md:26` | Verified - `app/static/js/shared/mobile-menu.jsx` |
| Route-based code splitting pattern | `static-assets.md:61-77` | Verified - `main.js:30-83` |
| Module init pattern (initXxx default export) | `static-assets.md:49-59` | Verified - `main.js:89` calls `module.default()` |
| Vite entry point `app/static/js/main.js` | `static-assets.md:126` | Verified - `vite.config.js:12` |
| Vite dev server port 3000 | `static-assets.md:130` | Verified - `vite.config.js:25` |
| Vite proxy to Flask 5000 | `static-assets.md:130` | Verified - `vite.config.js:27` |
| Admin breadcrumbs partial `_breadcrumbs.html` | `templates.md:26` | Verified - `app/templates/admin/_breadcrumbs.html` exists |
| Template filters registered in `app/filters.py` | `templates.md:76` | Verified - `app/filters.py` location |
| `markdown_safe` filter | `templates.md:77` | Verified - `app/filters.py:12-17` |
| `reading_time` filter | `templates.md:78` | Verified - `app/filters.py:19-25` |
| `sanitize_css` filter | `templates.md:79` | Verified - `app/filters.py:27-31` |
| `post_image_url` filter | `templates.md:80` | Verified - `app/filters.py:33-50` |
| `post_image_srcset` filter | `templates.md:81` | Verified - `app/filters.py:52-73` |
| `post_image_avif_url_stub` filter | `templates.md:82` | Verified - `app/filters.py:75-84` |
| Context processors in `app/context_processors.py` | `templates.md:86` | Verified - `app/context_processors.py` location |
| `inject_csrf()` context processor | `templates.md:87` | Verified - `context_processors.py:138-148` |
| `inject_config()` context processor | `templates.md:88-92` | Verified - `context_processors.py:150-161` |
| `inject_theme()` context processor | `templates.md:93` | Verified - `context_processors.py:163-165` |
| `inject_footer_data()` context processor | `templates.md:94` | Verified - `context_processors.py:167-191` |
| `inject_show_footer_posts()` context processor | `templates.md:95` | Verified - `context_processors.py:193-199` |
| `invalidate_settings_cache()` function | `templates.md:100` | Verified - `context_processors.py:30-32` |
| `invalidate_footer_cache()` function | `templates.md:101` | Verified - `context_processors.py:35-37` |
| Template inheritance pattern | `templates.md:66-72` | Verified - base.html is parent |
| All listed email templates exist | `templates.md:57-61` | Verified |
| Public comments partial exists | `templates.md:63` | Verified - `app/templates/public/comments.html` |

---

## 2. Inaccurate/Outdated Claims

| Claim | Doc Location | Actual Behavior | Correction Needed |
|-------|--------------|-----------------|-------------------|
| `image-review.js` referenced in code splitting | `static-assets.md:38` | File is named `image-preview.js`, not `image-review.js` | Rename doc reference or file |
| `image-review.js` in ROUTE_MODULES | `main.js:15,40,51` | References `'./image-review.js'` which doesn't exist | Should be `'./image-preview.js'` |
| `image-review.js` in moduleGlob | `main.js:15` | Imports `./image-review.js` which doesn't exist | Should be `./image-preview.js` |

---

## 3. Bugs Identified

| Severity | Location | Description |
|----------|----------|-------------|
| **High** | `main.js:15,40,51` | `image-review.js` is imported but the actual file is named `image-preview.js`. The file `app/static/js/image-preview.js` exists but is never loaded because `main.js` references the wrong filename. This breaks the image review functionality in admin posts/media routes. |

---

## 4. Missing Documentation

| Item | Evidence |
|------|----------|
| `image-preview.js` module not documented | File exists at `app/static/js/image-preview.js` but not listed in `static-assets.md` |
| `upload.js` module not documented | File exists at `app/static/js/upload.js` but not listed in `static-assets.md` |
| `lib/marked-wrapper.js` and `lib/marked.min.js` not documented | Files exist but not listed in static-assets.md structure |
| `prism.min.js` and `prism-languages.js` not in `app/static/js/lib/` | Document shows them at root level but they ARE at root level (correct) |

---

## 5. Recommended Improvements

### High Priority
- Fix the `image-review.js` vs `image-preview.js` naming inconsistency in `main.js` - either rename the import or rename the file to match documentation
- Update `static-assets.md` to document `image-preview.js` (not `image-review.js`)

### Medium Priority
- Add `upload.js` to the documented directory structure in `static-assets.md`
- Add `lib/marked-wrapper.js` and `lib/marked.min.js` to documented structure
- Add `image-preview.js` and `upload.js` to the Admin JS section

### Low Priority
- The `app/static/js/lib/` directory with `marked-wrapper.js` and `marked.min.js` is not documented but exists - consider adding to docs for completeness

---

## Summary

| Category | Count |
|----------|-------|
| Verified Accurate Claims | 30 |
| Inaccurate Claims | 3 |
| Bugs Identified | 1 |
| Missing Documentation | 4 |
| Improvements | 3 |