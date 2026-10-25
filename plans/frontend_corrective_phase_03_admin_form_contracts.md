# Frontend Corrective Phase 03 — Admin Form and Control Contracts

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/frontend/overview.md](../architecture/frontend/overview.md); this file is the historical record.

**Roadmap:** [frontend_corrective_roadmap.md](frontend_corrective_roadmap.md)
**Date:** 2026-10-23
**Status:** Complete
**Severity:** Critical / high — admin features that fail silently or are unreachable

## Objective

Repair the admin dashboard's form and control contracts. Every finding here is a case where a template declares an expectation (an attribute, a class, a header name, an element relationship) that the JavaScript or the server does not share.

## Findings

### FE-ADM-01 — Media uploads always fail with "No file selected." (critical)

`app/templates/admin/media.html` declares **two** file inputs:

```jinja
<!-- line 27 — outside the form, the one the JS actually uses -->
<input type="file" id="file-input" name="file" accept="image/png,..." hidden>

<!-- line 30 — inside the form, always empty, and named `file` -->
<form method="POST" action="{{ url_for('admin.upload_media') }}" id="upload-form" enctype="multipart/form-data">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <input type="file" id="file-input-hidden" name="file" accept="image/png,..." hidden>
</form>
```

`app/static/js/upload.js:66-67` then serialises the form *and* appends the real file:

```javascript
const formData = new FormData(uploadForm);   // includes the empty #file-input-hidden as `file`
formData.append('file', file);                // the real file is the SECOND `file` part
```

Werkzeug's `request.files["file"]` returns the **first** matching part, which is the empty one. The server therefore takes the empty branch:

```python
# app/routes/admin/media.py:134
if file.filename == "":
    flash("No file selected.", "error")
```

The admin can never upload an image through the UI.

### FE-ADM-02 — Theme Preview always returns 403 (high)

`app/templates/admin/settings.html:438` sends the CSRF token in a header:

```javascript
headers: { "X-CSRFToken": csrfToken, ... }
```

`app/csrf.py:63` reads a differently-spelled header:

```python
request.headers.get("X-CSRF-Token")
```

HTTP header names are case-insensitive but **not** hyphen-insensitive, so `X-CSRFToken` never matches `X-CSRF-Token`. The sibling implementation in `app/static/js/admin/editor.js:61` uses the correct name, which is why the editor preview works and the theme preview does not.

### FE-ADM-03 — Unsanitised HTML in the admin live preview (high, security)

```javascript
// app/static/js/admin/editor.js:41
previewDiv.innerHTML = marked.parse(text);
```

The server-side preview route sanitises the rendered markdown with `nh3`, but this client-side path does not. The Content-Security-Policy in `app/__init__.py:373` sets `script-src-attr 'unsafe-inline'`, so any inline event handler in the injected HTML executes. A post body containing raw HTML is therefore a stored-XSS vector against every admin who opens the editor for that post.

### FE-ADM-04 — Unescaped error string echoed into `innerHTML` (medium, security)

```javascript
// app/templates/admin/settings.html:447
previewContainer.innerHTML = `...<strong>Error:</strong> ${data.error}...`;
```

`data.error` originates from the server and reflects user-supplied theme input (`app/routes/admin/settings.py:203-204`). Inserting it through `innerHTML` is an injection sink. The defect is currently masked by FE-ADM-02 (the request never succeeds), so **fixing FE-ADM-02 makes this reachable** — the two must be fixed together.

### FE-ADM-05 — Analytics time-period select throws and never navigates (high)

```javascript
// app/static/js/shared/filter-select.js:14-19
document.querySelectorAll('select[data-auto-submit]').forEach(select => {
    select.addEventListener('change', () => {
        select.closest('form').classList.add('loading');
        window.location.href = select.value;
    });
});
```

`app/templates/admin/analytics.html:11` renders the select with `data-auto-submit` but **not inside a form** (the rendered ancestor chain is `html → body → main → div → div → div`). `select.closest('form')` therefore returns `null`, and `null.classList` throws a `TypeError` *before* `window.location.href` is assigned. The filter silently does nothing and the console shows an uncaught error.

### FE-ADM-06 — Audit log filter never applies (medium)

`app/templates/admin/audit.html:13` uses the same `data-auto-submit` mechanism, but with action names as option values (`user.created`, `post.published`, …) rather than the day counts the handler expects:

```javascript
const allowedDays = ['7', '30', '90', '365'];
if (!allowedDays.includes(value)) { return; }   // every audit option returns here
```

Every option exits silently, so the audit log filter has no effect.

### FE-ADM-07 — The mobile preview toggle never reveals the preview (high)

`app/static/js/admin/editor.js:13-25` toggles `preview-hidden`:

```javascript
if (isMobile) {
    editorSplit.classList.add('preview-hidden');
}
togglePreviewBtn.addEventListener('click', () => {
    const isHidden = editorSplit.classList.contains('preview-hidden');
    editorSplit.classList.toggle('preview-hidden');
    ...
});
```

But the mobile stylesheet gates visibility on a *different* class:

```css
/* app/static/css/admin.css:484-496 */
@media (max-width: 768px) {
    .editor-split .markdown-preview { display: none; }
    .editor-split.preview-visible .markdown-preview { display: block; }
}
```

Removing `preview-hidden` never adds `preview-visible`, so the preview stays hidden on mobile. The button's label also starts as "Show Preview" even when the preview is already hidden on load.

### FE-ADM-08 — The page editor has no preview split and no toggle (medium)

`app/templates/admin/page_editor.html:39` renders `<div class="editor-split">` with no `id` and no toggle button:

```jinja
<div class="editor-split">
    <div id="markdown-preview" class="markdown-preview prose">
```

`editor.js:13-14` looks up `#editor-split` and `#toggle-preview-btn`; both are `null` for this template, so the entire mobile-preview block is skipped. The page editor's preview therefore behaves differently from the post editor's, with no way to collapse it on a phone.

### FE-ADM-09 — Series drag-and-drop reorder cannot be submitted (medium)

`app/templates/admin/series_posts.html` renders a reorder form with a drag handle and `data-post-series-id` attributes, implying a drag-and-drop interface:

```jinja
<form method="POST" action="{{ url_for('admin.series_posts', series_id=series.id) }}" id="series-reorder-form">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <input type="hidden" name="action" value="reorder">
    {% for ps in series_posts %}
        <div class="series-post-item" data-post-series-id="{{ ps.id }}">
            <span class="drag-handle">⋮⋮</span>
            ...
            <input type="hidden" name="post_order[]" value="{{ ps.id }}">
```

The route **does** handle `action=reorder` and `post_order[]`, but the form has no submit control — the only button in the loop is the Remove button, which targets a different form via the `form=` attribute. No JavaScript implements the drag-and-drop either. The reorder path is therefore unreachable from the UI.

### FE-ADM-10 — Series "Remove" never shows a confirmation dialog (medium)

```jinja
<button type="submit" form="series-remove-{{ ps.id }}" class="btn btn-small btn-danger" data-confirm="Remove this post from the series?">Remove</button>
```

The shared confirmation helper binds to the **form**, not the button:

```javascript
// app/static/js/shared/utils.js:78
document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', e => { ... });
});
```

`data-confirm` here is on a `<button>`, and the form that actually submits (`#series-remove-N`) does not carry the attribute. The `submit` event fires on that form, which has no handler, so the destructive action proceeds with no confirmation.

### FE-ADM-11 — `data-loading` is inert across the admin (medium)

Six admin templates declare a loading state:

```jinja
<form method="POST" action="..." data-loading data-loading-text="Signing in...">
```

in `admin/login.html:7`, `admin/forgot-password.html:8`, `admin/reset-password.html:8`, `admin/tags.html:14`, `admin/users.html:85`, `admin/backup.html:11`, `admin/settings.html:15`.

No JavaScript reads `data-loading` or `data-loading-text` — a search of `app/static/js/` returns nothing. The intended effect (disable the submit button and show a pending label) never happens, so a slow request leaves the user with no feedback and an enabled button they can double-submit.

### FE-ADM-12 — `{% block title %}` is dead in every admin template (medium)

`app/templates/admin/base.html:20` renders a hardcoded title:

```jinja
<title>Admin | {{ site_title }}</title>
```

There is no `{% block title %}` in the admin root template, so the `{% block title %}` declared in all 12 admin child templates is silently discarded. Every admin page shares the title "Admin | <site title>", which is poor for browser history, bookmarks, and screen-reader page announcements.

`app/templates/admin/login_base.html` has the same defect.

### FE-ADM-13 — Editor draft keys collide between posts and pages (medium)

```javascript
// app/static/js/admin/editor.js:101-102
const idMatch = window.location.pathname.match(/\/edit\/(\d+)/);
const draftKey = idMatch ? `draft-${idMatch[1]}` : 'draft-new';
```

Post 5 and page 5 share `draft-5`; every "new post" and "new page" share `draft-new`. An admin with a new post open, who navigates to a new page, sees the other draft restored. The key must include the editor type.

### FE-ADM-14 — `bulk.js` dereferences a possibly-absent element (low, robustness)

```javascript
// app/static/js/admin/bulk.js:6
const bulkActions = document.getElementById('bulk-actions');
...
bulkActions.classList.toggle('hidden', !anyChecked);   // no null guard
```

The current templates (`admin/dashboard.html`, `admin/subscribers.html`) always provide both `#select-all` and `#bulk-actions`, so the defect is not currently reachable — but a template that adds a select-all without the actions bar will throw. The checkbox list is also captured once at init, so rows added later are not tracked.

## Fix specification

### 1. Media upload

Keep exactly one file input. The cleanest shape:

- keep `#file-input` **outside** the form (the JS reads its `files` list);
- remove the `name="file"` attribute from it, so it is never serialised;
- **delete** `#file-input-hidden` from inside the form.

Then in `upload.js`, build the body explicitly rather than from the form:

```javascript
const formData = new FormData();
formData.append('csrf_token', csrfToken);
formData.append('file', file);
```

This makes the multipart body independent of whatever the template happens to contain, and removes the class of bug permanently. If the form-based approach is kept instead, the in-form input must not carry `name="file"`.

### 2. CSRF header name

Standardise on `X-CSRF-Token` (the name the server reads and the name `editor.js` already uses). Change `admin/settings.html:438` to match.

Additionally, derive the header name in one place — `app/static/js/shared/utils.js` already exposes `getCsrfToken()`; add a `csrfHeaders()` helper there so no template hard-codes the header name, and add a test that asserts the name in the JavaScript matches the name in `app/csrf.py`.

### 3. Sanitise the client-side preview

The client-side preview must not be a weaker path than the server-side one. Options, in order of preference:

- **Preferred:** render the preview through the same sanitiser the server uses, exposed to the client. If `nh3` is not available in the browser bundle, apply an equivalent allowlist in JavaScript and strip event-handler attributes, `javascript:` URLs, and `<script>`/`<style>`/`<iframe>` elements.
- **Alternative:** drop the client-side rendering entirely and use only the debounced server-preview request, which is already implemented and already sanitised. The preview becomes slightly slower but the sanitisation is single-sourced.

Do not fix this by removing `script-src-attr 'unsafe-inline'` alone — inline handlers are one of several sinks and the CSP should be tightened in a separate, deliberate change.

### 4. Unescaped error echo

Replace the `innerHTML` assignment in `admin/settings.html:447` with `textContent` on a dedicated element, or escape the value before interpolation. The error is a human-readable message, not markup.

### 5. `data-auto-submit` handling

Split the two concerns currently conflated in `filter-select.js`:

- a **day-count** filter (`data-auto-submit` on a `<select>` whose values are `7/30/90/365`) that navigates to `?days=<value>`;
- a **form-submitting** filter for controls that live inside a form.

For the day-count case, navigate directly without touching `closest('form')`:

```javascript
if (allowedDays.includes(value)) {
    window.location.href = value;      // no form lookup
    return;
}
```

For a genuine in-form auto-submit, guard the lookup:

```javascript
const form = select.closest('form');
if (form) { form.classList.add('loading'); form.submit(); }
```

### 6. Audit log filter

Give the audit filter a distinct hook (for example `data-audit-filter`) with its own handler, rather than reusing the day-count contract. The audit page's options are action names, not day counts, and the two must not share a code path.

### 7 & 8. Preview split contract

Make `preview-visible` the single class that reveals the preview on mobile, and have the JavaScript manage it explicitly:

```javascript
const setPreviewVisible = (visible) => {
    editorSplit.classList.toggle('preview-visible', visible);
    editorSplit.classList.toggle('preview-hidden', !visible);
    const label = togglePreviewBtn.querySelector('.toggle-preview-text');
    if (label) label.textContent = visible ? 'Hide Preview' : 'Show Preview';
    togglePreviewBtn.setAttribute('aria-expanded', String(visible));
};
```

Apply this on load (reflecting the mobile default) and in the click handler, so the button label and `aria-expanded` are always accurate.

For `admin/page_editor.html`, add `id="editor-split"` and a `#toggle-preview-btn` so the page editor gets the same contract as the post editor. Alternatively, include the page editor's body area in the shared editor partial so the two cannot drift again.

### 9 & 10. Series reorder and remove

- **Reorder:** either implement the drag-and-drop interface the markup implies (a small pointer-events-based implementation that writes the new order into the existing `post_order[]` inputs and submits `#series-reorder-form`), or remove the drag handles and add an explicit "Save order" submit button to the form. The second is much cheaper and should be preferred unless drag-and-drop is a product requirement.
- **Remove:** move `data-confirm` onto the `#series-remove-N` form so the shared helper binds to it, and keep the visible button as a plain `type="submit"` with `form="series-remove-N"`. The helper's `pendingConfirmForm.submit()` path then works as designed.

### 11. Implement `data-loading`

Add the behaviour to `app/static/js/shared/utils.js` (or a dedicated module) so every declared form gets it:

```javascript
document.querySelectorAll('form[data-loading]').forEach(form => {
    form.addEventListener('submit', () => {
        const submit = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submit) {
            submit.disabled = true;
            submit.textContent = form.dataset.loadingText || submit.textContent;
        }
    });
});
```

### 12. Admin title block

Add `{% block title %}` to `admin/base.html` and `admin/login_base.html`:

```jinja
{% block title %}{% endblock %}
```

with the base providing a default via `{{ super() }}` or a sensible fallback, and have each admin template populate it.

### 13. Editor draft keys

Include the editor type in the key:

```javascript
const typeMatch = window.location.pathname.match(/\/admin\/(posts|pages)\//);
const type = typeMatch ? typeMatch[1] : 'post';
const draftKey = idMatch ? `draft-${type}-${idMatch[1]}` : `draft-${type}-new`;
```

### 14. `bulk.js` guards

Add null checks for `#bulk-actions` and `#bulk-form`, and re-query the checkbox list on each update so dynamically added rows are tracked.

## Tests

1. **Upload** — browser test: select a real image file, trigger the upload, assert the request succeeds and a new media card appears. Add a server-side test that posts a multipart body with a single `file` part and asserts success.
2. **CSRF header** — assert the header name used in the admin JavaScript equals the name read in `app/csrf.py` (a cross-file assertion is acceptable and prevents recurrence). Browser test: click Theme Preview, assert a successful response and rendered preview output.
3. **Preview XSS** — paste `<img src=x onerror="window.__xss=1">` into the editor body; assert the preview does not create an executable handler (check that no element in the preview has an `onerror` attribute) and that `window.__xss` is undefined. Repeat for `<script>` and `javascript:` URL payloads.
4. **Error echo** — submit a theme name containing `<img src=x onerror=alert(1)>`; assert the error message is rendered as text and no element is created from it.
5. **Analytics filter** — browser test: change the day select, assert the URL changes to include the day count and the page reloads, and assert no console error is raised.
6. **Audit filter** — browser test: select an action, assert the request is made with the action parameter.
7. **Preview toggle** — browser test at 375px: assert the preview is hidden initially, click the toggle, assert the preview becomes visible, assert the button label updates, assert `aria-expanded` reflects the state.
8. **Series** — browser test: assert the reorder form has a working submit path, and that clicking Remove opens the confirmation modal and that cancelling does not submit.
9. **`data-loading`** — browser test: submit a form with `data-loading`; assert the submit button is disabled and its text is replaced by `data-loading-text`.
10. **Title block** — assert each admin page's rendered `<title>` is distinct and contains the page's own name.
11. **Draft keys** — assert the post editor and the page editor derive different `localStorage` keys.
12. **`bulk.js`** — assert no uncaught error when `#bulk-actions` is absent.

## Expected files

- `app/templates/admin/media.html`
- `app/templates/admin/settings.html`
- `app/templates/admin/editor.html`
- `app/templates/admin/page_editor.html`
- `app/templates/admin/analytics.html`
- `app/templates/admin/audit.html`
- `app/templates/admin/series_posts.html`
- `app/templates/admin/base.html`
- `app/templates/admin/login_base.html`
- `app/static/js/upload.js`
- `app/static/js/admin/editor.js`
- `app/static/js/admin/bulk.js`
- `app/static/js/shared/filter-select.js`
- `app/static/js/shared/utils.js`
- `app/static/css/admin.css` (preview visibility classes)
- `tests/test_admin_contracts.py` (new)
- `tests/e2e/` — upload, preview toggle, and confirmation-modal interactions

## Acceptance criteria

- [ ] An admin can upload an image from the media library and see it in the grid.
- [ ] Theme Preview returns a successful response and renders the preview.
- [ ] The CSRF header name is defined in exactly one place and matches the server.
- [ ] Markdown payloads containing HTML cannot execute in the live preview.
- [ ] Theme error messages are rendered as text, never as markup.
- [ ] The analytics day filter changes the URL and reloads without a console error.
- [ ] The audit log action filter applies.
- [ ] The mobile preview toggle shows and hides the preview, with an accurate label and `aria-expanded`.
- [ ] The page editor exposes the same preview contract as the post editor.
- [ ] Series posts can be reordered and removed, and removal requires confirmation.
- [ ] Forms declaring `data-loading` disable their submit button and show the pending label.
- [ ] Every admin page has a distinct `<title>`.
- [ ] Post and page editor drafts do not share a `localStorage` key.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

FE-ADM-02 and FE-ADM-04 must be fixed in the same change. Must land after Phase 01 (both touch `admin/editor.html`) and before Phase 04 (Phase 04 changes the admin preview visibility CSS). Independent of Phase 02.

## Completion

**Status:** Complete — all 14 findings closed.

| Finding | Resolution |
|---|---|
| FE-ADM-01 | The duplicate hidden file input was removed. `upload.js` builds the multipart body explicitly (`csrf_token` + `file`), so the request no longer depends on template contents. A multipart POST with a single `file` part now succeeds and writes the file. |
| FE-ADM-02 | The CSRF header name is single-sourced in `app/csrf.py` as `CSRF_HEADER_NAME`, published to the browser as `data-csrf-header`, and consumed through `csrfHeaders()` in `app/static/js/shared/utils.js`. |
| FE-ADM-03 | The client-side `marked.parse` → `innerHTML` path was removed. The preview now goes through the server-sanitised route, so the client is no weaker than the server. The CSP was not weakened. |
| FE-ADM-04 | The theme error is rendered as text, never as markup. |
| FE-ADM-05 | The day-count filter navigates directly and the genuine in-form auto-submit path guards the `closest('form')` lookup. |
| FE-ADM-06 | The audit filter uses a distinct `data-audit-filter` hook with its own handler; it no longer shares a code path with the day filter. |
| FE-ADM-07 | `preview-visible` is the revealing class; `preview-hidden`, the label, and `aria-expanded` are managed together. `admin/shortcuts.js` was updated to delegate to the toggle button so the keyboard shortcut cannot fight the contract. |
| FE-ADM-08 | `admin/page_editor.html` now exposes the same `#editor-split` / `#toggle-preview-btn` contract as the post editor. |
| FE-ADM-09 | The series reorder form gained a working submit control and up/down move controls. |
| FE-ADM-10 | The series Remove path carries `data-confirm` on the **form**, so the shared helper's `form[data-confirm]` binding now reaches it. |
| FE-ADM-11 | `data-loading` is implemented in `app/static/js/shared/utils.js` and wired into `initSharedUtils()`; every `form[data-loading]` shows its pending label and disables its submit button. |
| FE-ADM-12 | The admin root templates now define a working `{% block title %}`, and each admin page renders a distinct title. |
| FE-ADM-13 | The post editor and the page editor derive different `localStorage` draft keys. |
| FE-ADM-14 | `bulk.js` guards the absent `#bulk-actions` element and re-queries the checkbox list on update. |

**Verification**

- `tests/test_admin_contracts.py` — 32 tests.
