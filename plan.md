# Consolidated Improvement Plan

**Status: COMPLETED (2026-04-02)**

All items from Waves 1-4 have been implemented. Wave 5 (Code Quality) was skipped as medium priority.

---

Consolidated from `plan2.md` (code quality), `plan4.md` (UI fixes), `plan5.md` (accessibility/UX), and `plan6.md` (enhancements).

All items verified against the codebase as of 2026-04-02.

## Testing

```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

---

## Wave 1: Bugs, Dead Code, and CSS Cleanup (COMPLETED)

All items in this wave are independent and can be implemented in parallel by separate agents.

### 1.1 Fix `rename_tag()` bug

**Verified:** `old_name = tag.name` is set AFTER `tag.name = new_name` (admin.py:927), so the log always shows the new name.

**Fix:** Move `old_name = tag.name` before `tag.name = new_name`.

- File: `app/routes/admin.py:925-927`

### 1.2 Fix `data-confirm` handler — broken feature

**Verified:** Line 11 of `main.js` has a comment `// --- Form delete confirmation via data-confirm attribute ---` but no code follows. All delete/restore/reset buttons use `data-confirm` attributes but no confirmation dialog ever appears — destructive actions execute immediately.

**Fix:** Insert form submit handler after line 11:

```js
document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', e => {
        if (!confirm(form.dataset.confirm)) e.preventDefault();
    });
});
```

- File: `app/static/js/main.js:11`

### 1.3 Remove dead bulk progress bar

**Verified:** Lines 25-63 inject a "Processing 0 of N..." progress bar during bulk form submit. The `MutationObserver` watches checkbox `checked` attribute changes, but the form submits via full page reload — the observer callback never fires.

**Fix:** Delete lines 25-63 entirely.

- File: `app/static/js/main.js:25-63`

### 1.4 Guard Ctrl+S and vim navigation to admin pages only

**Verified:** Both vim navigation (lines 538-570) and Ctrl+S (lines 572-622) fire on all pages. Ctrl+S blocks the browser's native "Save Page As" on public pages. Vim `g+d` navigates to `/admin/` from public pages. The `<body>` in admin/base.html has `class="admin-body"` but no JS checks it.

**Fix:** Wrap both handlers in `if (document.body.classList.contains('admin-body'))` guards. Also move modal close handlers (lines 624-638) inside the guard since the modal only exists on admin pages.

- File: `app/static/js/main.js:538-638`

### 1.5 Fix lazy image opacity fallback

**Verified:** CSS sets `img[loading="lazy"] { opacity: 0 }` (style.css:2254). JS adds `.loaded` class on load. But there's no `.js` class gate — if JS fails, all lazy images remain invisible.

**Fix:**
1. Add `document.documentElement.classList.add('js');` as first line of main.js (before `DOMContentLoaded`)
2. Gate the CSS: prefix `img[loading="lazy"]` rules with `.js`

- Files: `app/static/js/main.js` (line 1), `app/static/css/style.css:2254-2262`

### 1.6 Fix `--text-dim` contrast ratio — WCAG AA failure

**Verified:** `--text-dim: #656d76` on dark background `#0d1117` gives ~4.2:1 contrast. WCAG AA requires 4.5:1 for normal text.

**Fix:** `--text-dim: #7d8590` (gives ~4.6:1).

- File: `app/static/css/style.css:76`

### 1.7 Fix dark mode post card hover shadow

**Verified:** `.post-card:hover` uses `box-shadow: 0 12px 24px rgba(0,0,0,0.1)` — nearly invisible on dark background. No border-color transition.

**Fix:**
```css
.post-card {
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1), border-color var(--transition);
}
.post-card:hover {
    transform: translateY(-4px);
    border-color: var(--text-dim);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.3);
}
[data-theme="light"] .post-card:hover {
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
}
```

- File: `app/static/css/style.css:302-313`

### 1.8 Merge duplicate `.flash` CSS rule

**Verified:** Two separate `.flash` blocks exist (lines 1067-1073 with visual properties, lines 1109-1112 with layout properties). Should be merged.

**Fix:** Add `position: relative; overflow: hidden;` to the first block, delete the second block.

- File: `app/static/css/style.css:1067-1112`

### 1.9 Remove dead CSS rules

**Verified:** `.share-btn.twitter:hover`, `.share-btn.facebook:hover`, `.share-btn.linkedin:hover` on lines 572-574 never match — actual HTML uses `.share-btn.share-twitter` etc. Correctly-named rules already exist at lines 576-581.

**Fix:** Delete lines 572-574.

- File: `app/static/css/style.css:572-574`

### 1.10 Fix footer year logic

**Verified:** Footer shows `{% if current_year and current_year != 2026 %}{{ current_year }} - {% endif %}{{ current_year }}`. When year is 2027, shows "2027 - 2027".

**Fix:** Hardcode 2026 as start year:
```html
<p>&copy; 2026{% if current_year and current_year > 2026 %} - {{ current_year }}{% endif %} {{ site_title }}. Built with Flask.</p>
```

- File: `app/templates/base.html:106`

---

## Wave 2: Accessibility (WCAG Compliance) (COMPLETED)

All items are template changes to different files or CSS — fully parallelizable.

### 2.1 Add `aria-label` to form inputs

**Verified:** Dashboard search/filter inputs, tag create/rename inputs, and user password/username inputs all lack `aria-label`.

**Changes:**
- `app/templates/admin/dashboard.html:54` — add `aria-label="Search posts by title"` to search input
- `app/templates/admin/dashboard.html:55` — add `aria-label="Filter by status"` to filter select
- `app/templates/admin/tags.html:14` — add `aria-label="New tag name"` to create input
- `app/templates/admin/tags.html:29` — add `aria-label="Rename tag {{ tag.name }}"` to rename input
- `app/templates/admin/users.html:29` — add `aria-label="New password for {{ user.username }}"` to password input
- `app/templates/admin/users.html:60` — add `aria-label="Username"` to username input
- `app/templates/admin/users.html:61` — add `aria-label="Password"` to password input

### 2.2 Add `aria-label` to `<nav>` elements

**Verified:** Neither `base.html` nor `admin/base.html` have `aria-label` on their `<nav>` elements.

**Changes:**
- `app/templates/base.html:39` — `aria-label="Main navigation"`
- `app/templates/admin/base.html:14` — `aria-label="Admin navigation"`
- Add `aria-label="Pagination"` to all pagination `<nav>` elements in: `dashboard.html`, `subscribers.html`, `users.html`, `index.html`, `tag.html`, `search.html`

### 2.3 Fix keyboard shortcuts modal ARIA

**Verified:** Modal has `role="dialog"` and `aria-label` but is missing `aria-modal="true"` and `aria-labelledby`. The `<h2>` has no `id`.

**Fix:**
- Add `aria-modal="true" aria-labelledby="keyboard-help-title"` to `#keyboard-help`
- Add `id="keyboard-help-title"` to the `<h2>`

- File: `app/templates/admin/base.html:57-59`

### 2.4 Add vim navigation shortcuts to modal

**Verified:** Keyboard shortcuts modal doesn't list the vim navigation shortcuts (g+d, g+p, g+s, g+t).

**Fix:** Add navigation section to modal before Close button.

- File: `app/templates/admin/base.html` (before Close button)
- File: `app/static/css/style.css` — add `.shortcut-divider` styles

### 2.5 Add `datetime` attribute to `<time>` elements

**Verified:** `_post_content.html:12` and `post.html:110` (related posts) are missing `datetime` attributes.

**Changes:**
- `app/templates/_post_content.html:12` — add `datetime="{{ post.created_at.isoformat() }}"`
- `app/templates/post.html:110` — add `datetime="{{ rp.created_at.isoformat() }}"`

### 2.6 Add missing `{% block title %}` to admin templates

**Verified:** `users.html` and `backup.html` lack `{% block title %}`, so browser tabs show generic "Admin | {site_title}".

**Changes:**
- `app/templates/admin/users.html` — add `{% block title %}Users | Admin{% endblock %}`
- `app/templates/admin/backup.html` — add `{% block title %}Backups | Admin{% endblock %}`

---

## Wave 3: UX Improvements and Features (COMPLETED)

### 3.1 Fix nested forms in dashboard (invalid HTML)

**Verified:** The bulk `<form id="bulk-form">` wraps the entire post list (lines 65-124). Inside each post row, "Reset NL" and "Delete" are nested `<form>` elements. Browsers implicitly close the outer form, breaking bulk operations.

**Fix:** Move the bulk form to only contain the bulk action buttons. Use `form="bulk-form"` attribute on each checkbox to associate without nesting. Add JS for show/hide toggle.

- File: `app/templates/admin/dashboard.html:65-124`
- Add inline JS for selection toggle (see plan4.md Fix 1 for full template)

### 3.2 Hide dashboard bulk actions until items selected

**Verified:** Bulk action buttons (Publish, Unpublish, Delete) are always visible. The subscribers page already uses the correct pattern (hidden by default, shown via JS).

**Fix:** Add `hidden` class to `.bulk-actions` div, add JS to toggle visibility based on checkbox state. Can be combined with 3.1.

- File: `app/templates/admin/dashboard.html`

### 3.3 Admin nav dropdown for overcrowding

**Verified:** 10+ links crammed into one row. No grouping or dropdown.

**Fix:** Group 6 secondary links (Subscribers, Media, Tags, Users, Sessions, Backups) into a "More" dropdown. Keep View Site, Dashboard, Analytics, Logout as top-level.

- Files: `app/templates/admin/base.html`, `app/static/css/style.css`, `app/static/js/main.js`

### 3.4 Add keyboard shortcuts discoverability trigger

**Verified:** The `?` key opens the shortcuts modal, but there's no visible indicator.

**Fix:** Add a small `?` button to the admin nav. Add JS handler.

- Files: `app/templates/admin/base.html`, `app/static/js/main.js`

### 3.5 Add media upload UI

**Verified:** The media library only lists files — no upload form exists. No `upload_media` route exists.

**Fix:**
1. Add `POST /admin/media/upload` route using existing `_save_image()` helper
2. Add upload zone (drag-and-drop) to media.html template
3. Add CSS for upload zone
4. Add JS for drag-and-drop behavior

- Files: `app/routes/admin.py`, `app/templates/admin/media.html`, `app/static/css/style.css`, `app/static/js/main.js`

### 3.6 Replace inline style with CSS class

**Verified:** `sessions.html:29` has `style="font-size: 0.75rem;"`.

**Fix:** Add `.text-xs { font-size: 0.75rem; }` utility to style.css, replace inline style.

- Files: `app/templates/admin/sessions.html:29`, `app/static/css/style.css`

### 3.7 Add password complexity hints

**Verified:** Backend requires 8+ chars with 3 of 4 character classes, but UI only says "min 8 chars".

**Fix:** Add `<span class="label-hint text-muted">8+ chars with 3 of: lowercase, uppercase, digit, special</span>` after password inputs.

- File: `app/templates/admin/users.html`

---

## Wave 4: Backend Refactoring (COMPLETED)

Items in this wave modify different parts of the backend and are parallelizable.

### 4.1 Simplify `subscribe()` route logic

**Status:** IMPLEMENTED (2026-04-02)

Extracted helper functions `_reset_subscriber_token()`, `_send_or_flash_confirmation()`, `_try_send_confirmation()` to simplify the main flow and eliminate duplication.

- File: `app/routes/public.py:302-325`

### 4.2 Improve `edit_post()` error handling

**Status:** IMPLEMENTED (2026-04-02)

Extracted `_apply_post_updates()` helper function. Used in both normal and IntegrityError recovery paths to ensure consistent field updates.

- File: `app/routes/admin.py:712-720`

### 4.3 Extract CSV generation utility

**Status:** IMPLEMENTED (2026-04-02)

Created `app/csv_utils.py` with `generate_subscribers_csv()` function. Refactored both `export_subscribers()` and `subscribers_bulk()` to use the shared utility.

- Files: `app/routes/admin.py:825-850, 896-913`, new `app/csv_utils.py`

### 4.4 Extract magic numbers to configuration

**Status:** IMPLEMENTED (2026-04-02)

Added to `config.toml [app]`:
- `max_upload_size = 10485760` (10MB)
- `export_batch_size = 500`
- `fts_result_limit = 100`
- `token_enumeration_delay = 0.1`

Added to `config.toml [email]`:
- `smtp_timeout = 30`

- Files: `config.toml`, `app/config.py`, `app/routes/admin.py`, `app/email.py`, `app/routes/public.py`, `app/search.py`

### 4.5 Add validation for empty tag names

**Status:** IMPLEMENTED (previously)

Empty tags are skipped with warning flash message in `_get_or_create_tags()`.

- File: `app/routes/admin.py:690-710`

---

## Wave 5: Code Quality

Lower priority polish — parallelizable.

### 5.1 Break down large functions

Targets: `edit_post()` (~90 lines), `new_post()` (~60 lines), `dashboard()` (~50 lines), `_get_analytics_data()` (~90 lines).

- File: `app/routes/admin.py`

### 5.2 Improve type hints

Add comprehensive type hints to all public functions. Use `TypedDict`, `Literal` where appropriate.

### 5.3 Add comprehensive docstrings

Google-style docstrings for all public functions and classes.

---

## Wave 6: Enhancements (Future)

Lower priority items from plan6.md and plan2.md P3.

### 6.1 Admin navigation icons
Add small SVG icons to nav items for faster visual scanning.

### 6.2 Editor character counters
Title (max 200 chars), summary (max 500 chars) with real-time counters.

### 6.3 Enhanced autosave indicator
More prominent with checkmark/warning icons and relative time display.

### 6.4 Search UX improvements
Recent searches dropdown, search result highlighting, scope selector.

### 6.5 Command palette (Cmd+K)
Quick navigation to posts, tags, and admin sections.

### 6.6 Improve test coverage
Run `pytest --cov=app tests/`, add tests for subscribe edge cases, edit_post error paths, concurrent access.

### 6.7 Add rate limiting documentation
Create docs with nginx/caddy/Cloudflare examples. Reference from DEPLOY.md.

---

## Wave Dependency Graph

```
Wave 1 (Bugs/CSS)  ──────────────────────────┐
Wave 2 (Accessibility)  ──────────────────────┼──> All independent, can run in parallel
Wave 3 (UX/Features)  ────────────────────────┤
Wave 4 (Backend Refactoring)  ────────────────┤
Wave 5 (Code Quality)  ───────────────────────┘
Wave 6 (Enhancements)  ── depends on Wave 3 completion for some items
```

Within each wave, all items are independent unless noted.

Wave 3 item 3.1 (nested forms) and 3.2 (bulk actions hide) both modify `dashboard.html` and should be done together.

Wave 3 item 3.3 (nav dropdown) and 3.4 (keyboard discoverability) both modify `admin/base.html` nav section and should be done together.

Wave 3 items 3.3, 3.4, 3.5 all add to `main.js` and `style.css` — coordinate CSS additions to avoid conflicts.

## File Change Summary

| File | Waves | Items |
|------|-------|-------|
| `app/static/js/main.js` | 1, 3 | 1.2, 1.3, 1.4, 1.5, 3.3, 3.4, 3.5 |
| `app/static/css/style.css` | 1, 3 | 1.5, 1.6, 1.7, 1.8, 1.9, 3.3, 3.5, 3.6 |
| `app/templates/admin/dashboard.html` | 1, 2, 3 | 1.10 via base, 2.1, 2.2, 3.1, 3.2 |
| `app/templates/admin/base.html` | 2, 3 | 2.2, 2.3, 2.4, 3.3, 3.4 |
| `app/templates/admin/users.html` | 2, 3 | 2.1, 2.6, 3.7 |
| `app/templates/admin/tags.html` | 2 | 2.1 |
| `app/templates/admin/media.html` | 3 | 3.5 |
| `app/templates/admin/sessions.html` | 3 | 3.6 |
| `app/templates/admin/backup.html` | 2 | 2.6 |
| `app/templates/base.html` | 1, 2 | 1.10, 2.2 |
| `app/templates/_post_content.html` | 2 | 2.5 |
| `app/templates/post.html` | 2 | 2.5 |
| `app/templates/index.html` | 2 | 2.2 |
| `app/templates/tag.html` | 2 | 2.2 |
| `app/templates/search.html` | 2 | 2.2 |
| `app/routes/admin.py` | 1, 3, 4 | 1.1, 3.5, 4.2, 4.3, 4.4, 4.5 |
| `app/routes/public.py` | 4 | 4.1, 4.4 |
| `app/csv_utils.py` | 4 | 4.3 |
| `app/email.py` | 4 | 4.4 |
| `app/search.py` | 4 | 4.4 |
| `config.toml` | 4 | 4.4 |
| `app/config.py` | 4 | 4.4 |

---

## Code Review Checklist (per wave)

### Security
- [ ] No new SQL injection vulnerabilities
- [ ] No new XSS vulnerabilities
- [ ] CSRF protection maintained
- [ ] File upload validation maintained
- [ ] No sensitive data in logs

### Functionality
- [ ] All existing features work as before
- [ ] Edge cases handled (empty inputs, None values)
- [ ] Race conditions considered

### Code Quality
- [ ] Follows existing code style
- [ ] No code duplication
- [ ] Functions appropriately sized

### Testing
- [ ] Tests pass: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`
- [ ] Manual verification for UI changes

---

*Created: 2026-04-02*
*Sources: plan2.md, plan4.md, plan5.md, plan6.md (removed after consolidation)*
