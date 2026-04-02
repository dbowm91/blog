# UI Improvements Plan — High Priority Fixes

## Summary
Fix 4 high-priority UI issues: nested forms (invalid HTML), admin nav overcrowding, dark mode hover shadows, and missing media upload UI.

---

## 1. Fix Nested Forms in Dashboard (Invalid HTML)

**Problem:** `admin/dashboard.html` has `<form>` elements nested inside the outer `<form id="bulk-form">`. The "Reset NL" and per-post "Delete" forms inside each `.post-list-item` are children of the bulk operations form. This is invalid HTML — forms cannot be nested.

**Files:** `app/templates/admin/dashboard.html`

**Fix:**
1. Remove the outer `<form id="bulk-form">` wrapper around the entire post list
2. Move the bulk form to only contain the checkbox + bulk action buttons (in the `.bulk-actions` div)
3. Use `form="bulk-form"` attribute on each checkbox `<input>` to associate them with the bulk form without nesting
4. Add `hidden` class to `.bulk-actions` and show/hide via JS (same pattern as subscribers.html)

**Template changes:**
```html
<!-- Replace the bulk form section (lines 64-127) -->
<div class="bulk-actions hidden" id="bulk-actions">
    <form method="POST" action="{{ url_for('admin.bulk_operations') }}" id="bulk-form" class="flex-row gap-sm items-center">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <input type="checkbox" id="select-all-posts" aria-label="Select all posts">
        <button type="submit" name="action" value="publish" class="btn btn-small btn-ghost" data-confirm-bulk="Publish selected posts?">Publish</button>
        <button type="submit" name="action" value="unpublish" class="btn btn-small btn-ghost" data-confirm-bulk="Unpublish selected posts?">Unpublish</button>
        <button type="submit" name="action" value="delete" class="btn btn-small btn-danger" data-confirm-bulk="Delete selected posts? This cannot be undone.">Delete</button>
    </form>
</div>

<div class="post-list">
    ...
    {% for post in posts %}
        <div class="post-list-item">
            <input type="checkbox" name="post_ids" value="{{ post.id }}" class="bulk-checkbox" form="bulk-form">
            ...
        </div>
    {% endfor %}
</div>
```

**JS changes (add inline script at bottom of dashboard.html, same pattern as subscribers.html):**
```html
<script nonce="{{ csp_nonce }}">
(function() {
    var form = document.getElementById('bulk-form');
    var bulkActions = document.getElementById('bulk-actions');
    var selectAll = document.getElementById('select-all-posts');

    function updateBulkUI() {
        var checked = form.querySelectorAll('.bulk-checkbox:checked');
        if (checked.length > 0) {
            bulkActions.classList.remove('hidden');
        } else {
            bulkActions.classList.add('hidden');
        }
    }

    form.querySelectorAll('.bulk-checkbox').forEach(function(cb) {
        cb.addEventListener('change', updateBulkUI);
    });

    if (selectAll) {
        selectAll.addEventListener('change', function() {
            form.querySelectorAll('.bulk-checkbox').forEach(function(cb) {
                cb.checked = selectAll.checked;
            });
            updateBulkUI();
        });
    }
})();
</script>
```

**CSS addition (style.css):**
```css
.bulk-actions.hidden {
    display: none;
}
```

---

## 2. Fix Admin Nav Overcrowding

**Problem:** Admin navbar has 10+ links (View Site, Dashboard, Analytics, Subscribers, Media, Tags, Users, Sessions, Backups, Logout). On screens 1100-1300px wide, this overflows.

**Files:** `app/templates/admin/base.html`, `app/static/css/style.css`, `app/static/js/main.js`

**Fix:** Group secondary nav links into a "More" dropdown menu.

**Template changes (admin/base.html):**
```html
<div class="nav-links">
    <a href="{{ url_for('public.index') }}">View Site</a>
    <a href="{{ url_for('admin.dashboard') }}" {% if request.endpoint == 'admin.dashboard' %}class="active"{% endif %}>Dashboard</a>
    <a href="{{ url_for('admin.analytics') }}" {% if request.endpoint == 'admin.analytics' %}class="active"{% endif %}>Analytics</a>

    <!-- Dropdown for secondary links -->
    <div class="nav-dropdown">
        <button type="button" class="nav-link-btn nav-dropdown-toggle" aria-expanded="false" aria-haspopup="true">
            More
            <svg class="dropdown-arrow" viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><path d="M7 10l5 5 5-5z"/></svg>
        </button>
        <div class="nav-dropdown-menu">
            <a href="{{ url_for('admin.subscribers') }}" {% if request.endpoint == 'admin.subscribers' %}class="active"{% endif %}>Subscribers</a>
            <a href="{{ url_for('admin.media') }}" {% if request.endpoint == 'admin.media' %}class="active"{% endif %}>Media</a>
            <a href="{{ url_for('admin.tags_list') }}" {% if request.endpoint == 'admin.tags_list' %}class="active"{% endif %}>Tags</a>
            <a href="{{ url_for('admin.users_list') }}" {% if request.endpoint == 'admin.users_list' %}class="active"{% endif %}>Users</a>
            <a href="{{ url_for('admin.sessions_list') }}" {% if request.endpoint == 'admin.sessions_list' %}class="active"{% endif %}>Sessions</a>
            <a href="{{ url_for('admin.backup') }}" {% if request.endpoint == 'admin.backup' %}class="active"{% endif %}>Backups</a>
        </div>
    </div>

    <span class="nav-separator" aria-hidden="true"></span>
    <form method="POST" action="{{ url_for('admin.logout') }}" class="inline-form">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <button type="submit" class="nav-link-btn">Logout</button>
    </form>
</div>
```

**CSS additions (style.css):**
```css
/* Nav dropdown */
.nav-dropdown {
    position: relative;
}

.nav-dropdown-toggle {
    display: flex;
    align-items: center;
    gap: 4px;
}

.dropdown-arrow {
    transition: transform 0.2s ease;
}

.nav-dropdown.open .dropdown-arrow {
    transform: rotate(180deg);
}

.nav-dropdown-menu {
    position: absolute;
    top: 100%;
    right: 0;
    min-width: 160px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 8px 0;
    opacity: 0;
    visibility: hidden;
    transform: translateY(-8px);
    transition: opacity 0.2s ease, transform 0.2s ease, visibility 0.2s ease;
    z-index: 200;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.nav-dropdown.open .nav-dropdown-menu {
    opacity: 1;
    visibility: visible;
    transform: translateY(4px);
}

.nav-dropdown-menu a {
    display: block;
    padding: 8px 16px;
    color: var(--text-muted);
    font-size: 0.875rem;
    transition: color var(--transition), background var(--transition);
}

.nav-dropdown-menu a:hover {
    color: var(--text);
    background: var(--bg-elevated);
}

.nav-dropdown-menu a.active {
    color: var(--accent);
    background: var(--accent-dim);
}

.nav-dropdown-menu a.active::after {
    display: none;
}

@media (max-width: 768px) {
    .nav-dropdown-menu {
        position: static;
        opacity: 1;
        visibility: visible;
        transform: none;
        box-shadow: none;
        border: none;
        background: transparent;
        padding-left: 16px;
    }
    .nav-dropdown.open .nav-dropdown-menu {
        transform: none;
    }
}
```

**JS additions (main.js, inside DOMContentLoaded):**
```js
// Nav dropdown toggle
document.querySelectorAll('.nav-dropdown-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
        const dropdown = btn.closest('.nav-dropdown');
        const isOpen = dropdown.classList.toggle('open');
        btn.setAttribute('aria-expanded', isOpen.toString());
    });
});

// Close dropdown on outside click
document.addEventListener('click', (e) => {
    if (!e.target.closest('.nav-dropdown')) {
        document.querySelectorAll('.nav-dropdown.open').forEach(d => {
            d.classList.remove('open');
            d.querySelector('.nav-dropdown-toggle')?.setAttribute('aria-expanded', 'false');
        });
    }
});
```

---

## 3. Fix Dark Mode Post Card Hover Shadow

**Problem:** Post card hover uses `box-shadow: 0 12px 24px rgba(0,0,0,0.1)` which is nearly invisible on the dark background `--bg: #0d1117`.

**Files:** `app/static/css/style.css`

**Fix:** Increase shadow opacity for dark mode and add a border-color shift as the primary hover indicator.

**CSS changes (style.css):**
```css
/* Replace the existing .post-card:hover rule */
.post-card:hover {
    transform: translateY(-4px);
    border-color: var(--text-dim);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.3);
}

/* Add light mode override */
[data-theme="light"] .post-card:hover {
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
}
```

---

## 4. Add Media Upload UI

**Problem:** The media library (`/admin/media`) shows existing files but has no upload form. Users must upload images through the post editor, which is poor discoverability.

**Files:** `app/routes/admin.py`, `app/templates/admin/media.html`, `app/static/css/style.css`

**Route addition (admin.py, after `delete_media` route ~line 887):**
```python
@admin.route("/media/upload", methods=["POST"])
@admin_required
def upload_media() -> Response:
    """Upload one or more image files to the media library."""
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        flash("No files selected.", "error")
        return redirect(url_for("admin.media"))

    uploaded = 0
    errors = []
    for f in files:
        if not f.filename:
            continue
        filename, error = _save_image(f)
        if error:
            errors.append(f"{f.filename}: {error}")
        elif filename:
            uploaded += 1
        # If both None, file was not an allowed type — silently skip

    if uploaded:
        flash(f"Uploaded {uploaded} file(s).", "success")
    if errors:
        for err in errors:
            flash(err, "error")
    return redirect(url_for("admin.media"))
```

**Template changes (admin/media.html):**
Replace the entire block content with:
```html
{% extends "admin/base.html" %}

{% block title %}Media Library | Admin{% endblock %}

{% block content %}
<div class="dashboard animate-in">
    <div class="dashboard-header">
        <h1>Media Library</h1>
    </div>

    <!-- Upload zone -->
    <form method="POST" action="{{ url_for('admin.upload_media') }}" class="upload-zone" id="upload-zone" enctype="multipart/form-data">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <div class="upload-zone-content">
            <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor" class="upload-icon"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/></svg>
            <p class="upload-text">Drag & drop images here, or <label for="file-input" class="upload-browse">browse</label></p>
            <p class="upload-hint">PNG, JPG, GIF, WebP — max 10MB each</p>
            <input type="file" id="file-input" name="files" multiple accept="image/png,image/jpeg,image/gif,image/webp" class="sr-only">
        </div>
        <button type="submit" class="btn btn-primary upload-submit-btn">Upload</button>
    </form>

    {% if files %}
    <div class="media-grid">
        {% for f in files %}
        <div class="media-card">
            <div class="media-card-img">
                <img src="{{ url_for('static', filename='uploads/' + f.name) }}" alt="{{ f.name }}" loading="lazy" decoding="async">
            </div>
            <div class="media-card-info">
                <span class="media-name" title="{{ f.name }}">{{ f.name }}</span>
                <span class="media-size">{{ (f.size / 1024) | round(1) }} KB</span>
            </div>
            <div class="media-card-actions">
                <button class="btn btn-small btn-ghost media-copy-btn" data-url="{{ url_for('static', filename='uploads/' + f.name) }}" type="button">Copy URL</button>
                <form method="POST" action="{{ url_for('admin.delete_media', filename=f.name) }}" class="inline-form" data-confirm="Delete {{ f.name }}?">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                    <button type="submit" class="btn btn-small btn-danger">Delete</button>
                </form>
            </div>
        </div>
        {% endfor %}
    </div>
    {% if truncated %}
    <p class="flash flash-warning mt-md">Showing first 1000 files only.</p>
    {% endif %}
    {% if total_pages > 1 %}
    <nav class="pagination mt-md" aria-label="Pagination">
        {% if page > 1 %}
        <a href="{{ url_for('admin.media', page=page-1) }}" class="page-link">&larr; Newer</a>
        {% endif %}
        <span class="page-info">Page {{ page }} of {{ total_pages }}</span>
        {% if page < total_pages %}
        <a href="{{ url_for('admin.media', page=page+1) }}" class="page-link">Older &rarr;</a>
        {% endif %}
    </nav>
    {% endif %}
    {% else %}
    <div class="empty-state">
        <h3>No media files</h3>
        <p>Upload images using the form above, or attach them when creating posts.</p>
    </div>
    {% endif %}
</div>
{% endblock %}
```

**CSS additions (style.css):**
```css
/* Upload zone */
.upload-zone {
    border: 2px dashed var(--border);
    border-radius: var(--radius-lg);
    padding: 40px;
    text-align: center;
    margin-bottom: 32px;
    background: var(--bg-surface);
    transition: border-color 0.2s ease, background var(--transition);
    position: relative;
}

.upload-zone.drag-over {
    border-color: var(--accent);
    background: var(--accent-dim);
}

.upload-zone-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
}

.upload-icon {
    color: var(--text-dim);
}

.upload-text {
    color: var(--text-muted);
    font-size: 0.95rem;
}

.upload-browse {
    color: var(--accent);
    cursor: pointer;
    text-decoration: underline;
}

.upload-browse:hover {
    color: var(--accent-hover);
}

.upload-hint {
    color: var(--text-dim);
    font-size: 0.8rem;
}

.upload-submit-btn {
    margin-top: 16px;
}

[data-theme="light"] .upload-zone {
    background: #f6f8fa;
}
```

**JS additions (main.js, inside DOMContentLoaded):**
```js
// Drag and drop for media upload
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');

if (uploadZone && fileInput) {
    ['dragenter', 'dragover'].forEach(event => {
        uploadZone.addEventListener(event, (e) => {
            e.preventDefault();
            uploadZone.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(event => {
        uploadZone.addEventListener(event, (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-over');
        });
    });

    uploadZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
        }
    });

    uploadZone.addEventListener('click', (e) => {
        if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'LABEL') {
            fileInput.click();
        }
    });
}
```

---

## Files Modified (summary)

| File | Changes |
|------|---------|
| `app/templates/admin/dashboard.html` | #1 — Restructure bulk form, add inline JS |
| `app/templates/admin/base.html` | #2 — Dropdown menu for secondary nav links |
| `app/templates/admin/media.html` | #4 — Upload zone, `{% block title %}`, aria-label on pagination |
| `app/routes/admin.py` | #4 — `upload_media()` route |
| `app/static/css/style.css` | #2, #3, #4 — Dropdown CSS, hover shadow fix, upload zone CSS |
| `app/static/js/main.js` | #2, #4 — Dropdown toggle, drag-and-drop handlers |

---

## Testing

Run the existing test suite after all changes:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

Manual checks:
- [ ] Dashboard delete/reset buttons work without nested form issues
- [ ] Bulk actions hidden until posts selected, then appear
- [ ] Admin nav dropdown opens/closes correctly
- [ ] Admin nav fits on 1100px-wide screens
- [ ] Post card hover shadow visible on dark mode
- [ ] Media upload drag-and-drop works
- [ ] Media upload via file browser works
- [ ] Multiple file upload works
- [ ] Invalid file types rejected with error message
