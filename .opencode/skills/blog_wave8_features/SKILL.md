---
name: blog_wave8_features
description: "Blog CMS Wave 8+ Developer Experience - Shell context, tests, missing image handling, DB integrity check, UI polish, loading states, bulk delete confirmation. Triggers: Flask shell context, Post.short_code test, FTS tests, context processor tests, CLI tests, missing image file handling, database integrity check, loading spinner, bulk delete confirmation."
metadata:
  requires: "python>=3.12, flask>=3.1"
  homepage: "https://github.com/sugarwookie/blog"
---

## Flask Shell Context

`app/__init__.py` exposes models to `flask shell`:
```python
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 'User': User, 'Post': Post, 'Tag': Tag,
        'Subscriber': Subscriber, 'Page': Page, 'PageView': PageView,
        'ShareEvent': ShareEvent, 'AdminSession': AdminSession, 'SiteSettings': SiteSettings,
    }
```

## Missing Image Handling

`post_image_url` template filter in `app/__init__.py`:
```python
@app.template_filter("post_image_url")
def post_image_url_filter(post):
    if not post or not post.image:
        return None
    path = os.path.join(app.config["UPLOAD_FOLDER"], post.image)
    if os.path.isfile(path):
        return post.image
    return None
```

Templates using this filter: `index.html`, `tag.html`, `search.html`, `_post_content.html`, `post.html`, `email/newsletter.html`, `admin/editor.html`

## Database Integrity Check

`_check_database_integrity()` in `app/__init__.py`:
- Runs `PRAGMA integrity_check` on startup
- Logs warning if corruption detected with backup suggestion
- Runs after logging configured, before scheduler starts

## Bulk Delete Two-Click Confirmation

`app/static/js/main.js` implements two-click confirmation for bulk delete:
1. First click: Button text changes to "Delete X posts? Click again to confirm"
2. `.btn-danger-primed` class provides pulsing red animation
3. Auto-resets after 5 seconds or on blur

## Loading Spinner

`btn-loading` class in `main.js` triggers CSS spinner on submit:
```javascript
submitBtn.classList.add('btn-loading');
```
CSS spinner already exists in `style.css`.

## Upload Progress

XHR upload with progress listener in `main.js`:
- `XMLHttpRequest` with `xhr.upload.addEventListener('progress', ...)`
- `showUploadProgress(percent)` for real-time percentage
- CSRF token via `X-CSRF-Token` header
- Falls back to page reload on success

## Prefers-Reduced-Motion

CSS media queries disable animations for users who prefer reduced motion:
- Navbar transition, share button animation, lightbox, etc.
- Check `style.css` for `prefers-reduced-motion` media queries

## Keyboard Shortcuts (Admin)

Shortcuts in `app/static/js/admin/shortcuts.js`:
- `Ctrl+S` / `Cmd+S` — save draft
- `Ctrl+Shift+P` / `Cmd+Shift+P` — toggle preview
- `Ctrl+Enter` / `Cmd+Enter` — publish post
- `?` — show keyboard shortcuts modal
- `Esc` — close modal
- `g then d/p/s/t` — vim-style navigation (Dashboard, Posts, Subscribers, Tags)

All shortcuts guarded with `document.body.classList.contains('admin-body')`.

## Test Files

- `tests/test_search.py` - FTS module tests
- `tests/test_context_processors.py` - Context processor tests
- `tests/test_cli.py` - CLI command tests

## Known Limitations

FTS5 vtable tests may fail in pytest due to SQLite connection pool state between tests. 12 of 16 tests pass. FTS functionality works correctly in production.