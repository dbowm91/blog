# Site Identity Phase 01 — Admin Settings Reorganisation and Site Customisation

**Roadmap:** [site_identity_authoring_roadmap.md](site_identity_authoring_roadmap.md)
**Date:** 2026-10-24
**Status:** Planned
**Severity:** High — the settings page cannot express three of the site-level controls the operator asked for, and the theme preview is below the control it previews.

## Objective

Make `/admin/settings` a complete site-settings surface:

1. Put the theme preview **above** the theme selector and show it by default,
   so an admin can see the effect of a theme without scrolling and without
   pressing a button first.
2. Add a comments on/off switch that actually turns comment submission and
   the comment block off across the public site.
3. Add an editable site footer.

## Findings

### SIA-01 — The theme preview sits below the theme selector (high)

`app/templates/admin/settings.html` orders the settings sections as:

| Order | Section | Line |
|---|---|---|
| 0 | Theme | 13 |
| 1 | Theme Preview | 141 |
| 2 | Theme Registry | 161 |

Measured in Chromium against `http://localhost:5050/admin/settings`:

```
settings section order: [{i:0, heading:'Theme'}, {i:1, heading:'Theme Preview'}, {i:2, heading:'Theme Registry'}]
```

The preview is the *result* of the selectors in the section above it, so the
operator has to scroll past the control to reach the feedback and then scroll
back to change the selection.

### SIA-02 — The theme preview is hidden until a button is pressed (high)

The section carries an inline `style="display: none;"`:

```html
<!-- app/templates/admin/settings.html:141 -->
<div class="settings-section" id="theme-preview-section" style="display: none;">
```

Measured: `preview section state: {"inlineDisplay": "none", "computed": "none"}`.

The preview is only populated by `fetchPreview()` in the page's inline script,
which is bound to the `.theme-preview-btn` elements. On load the container
still holds its placeholder copy ("Click \"Preview\" to see theme styling"),
hidden. The admin sees no preview at all until they press Preview.

The preview request itself is correct — `fetchPreview` sends the *selected*
values from both selects, so a preview reflects an unsaved selection. That
behaviour must be preserved when the preview is made to load on demand.

### SIA-03 — There is no comments on/off control (high)

`site_settings` has no comments column, and the public comment endpoint is
unconditional. There is no way to close comments for a maintenance window, a
campaign, or a site that does not want them.

### SIA-04 — The site footer is hardcoded (medium)

`app/templates/base.html` renders a fixed footer:

```html
<footer class="footer" id="footer" aria-label="Site footer">
    <div class="container footer-grid">
        {% if show_footer_posts %}
        <div class="footer-section">
            <h3 class="footer-heading">Latest from the blog</h3>
            ...
        </div>
        {% endif %}
        <div class="footer-section">
            <h3 class="footer-heading">Browse by tag</h3>
            ...
        </div>
    </div>
    <div class="container footer-bottom">
        <p>&copy; {{ current_year }} {{ site_title }}. Built with Flask.</p>
    </div>
</footer>
```

The bottom line is fixed markup. The admin cannot change the copyright line,
add a tagline, or remove either footer column. Measured: the `/admin/settings`
body contains no occurrence of "footer".

### SIA-05 — The settings page has no non-theme section (medium)

`/admin/settings` is theme-only. There is nowhere to put the controls in SIA-03
and SIA-04, and mixing site fields into the Theme form would couple them to
theme validation — a bad theme name currently redirects the whole form away
before anything else is written. A separate **Site** section with its own form
and endpoint keeps one owner per value and keeps the failure modes separate.

## Fix specification

### 1. Move and auto-populate the theme preview

In `app/templates/admin/settings.html`:

- Move the `#theme-preview-section` block **above** the Theme section, so the
  order becomes: Theme Preview, Theme, Theme Registry.
- Remove the inline `style="display: none;"`. The section is visible by
  default; `fetchPreview` already sets `previewSection.style.display = 'block'`
  on every path, so the attribute is the only thing keeping it hidden.
- On load, request the preview for the **currently selected** values (the
  saved theme), so the admin sees the live theme before touching anything.
- Keep the existing `.theme-preview-btn` buttons. They must still preview the
  *selected but unsaved* values — that is the whole point of the preview.
- Add a light/dark switch inside the preview container so both schemes can be
  compared without changing the saved setting. The existing
  `data-target="light"` / `data-target="dark"` buttons already drive
  `previewContainer.setAttribute('data-color-scheme', target)`; the switch must
  reuse that same code path rather than introduce a second one.
- Do not weaken the CSP. The preview stylesheet is injected with
  `style.setAttribute('nonce', ...)` — keep the nonce.

Guard the auto-preview so it cannot fire before the DOM is ready and so a
failed request leaves the placeholder message in place rather than an empty box.

### 2. Comments switch

Model (`app/models.py`, `SiteSettings`):

```python
comments_enabled = db.Column(db.Boolean, default=True, nullable=False)
```

Service (`app/services/site_settings.py`, new): a `validate_site_settings()`
function that owns the parsing of the site-settings form payload and returns a
clean dict, mirroring the shape of `app/services/theme_settings.py`. The route
must not parse raw form values inline.

Admin route (`app/routes/admin/settings.py`): new endpoint
`POST /admin/settings/site`, `@admin_required`, persisting:

- `comments_enabled` — checkbox, `request.form.get("comments_enabled") == "on"`.
- `footer_text` — free text, trimmed, capped at 300 characters.
- `footer_show_posts` — checkbox; hides the "Latest from the blog" column.
- `footer_show_tags` — checkbox; hides the "Browse by tag" column.

On success: `db.session.commit()` then `invalidate_settings_cache()`.

Public enforcement (fail closed):

- `app/routes/public/comments.py` — the POST handler must refuse to create a
  comment when comments are disabled. It must return the same
  `redirect(url_for('public.post', slug=slug))` with an error flash, **not** a
  500 and not a silent success.
- The comment block must not render when comments are disabled. The flag is
  read in `app/context_processors.py` and exposed as `comments_enabled`.
  `app/templates/post.html` wraps the `<section class="comments">` in
  `{% if comments_enabled %}`.
- Existing comments stay visible when comments are switched off — the switch
  closes the door, it does not delete the conversation. The section header
  should say that commenting is closed.

Read path: the flag must be read without `SiteSettings.get_instance()` on the
public path. `get_instance()` performs `db.session.flush()`, which flushes any
other pending changes in the session as a side effect. Use the cached settings
read (`invalidate_settings_cache()` / the `site_settings` cache key) that the
theme service already maintains, or a plain `select()`.

### 3. Editable footer

Model:

```python
footer_text = db.Column(db.String(300), default="", nullable=False)
footer_show_posts = db.Column(db.Boolean, default=True, nullable=False)
footer_show_tags = db.Column(db.Boolean, default=True, nullable=False)
```

Template (`app/templates/base.html`):

```jinja
<div class="container footer-bottom">
    {% if footer_text %}
    <p class="footer-text">{{ footer_text }}</p>
    {% else %}
    <p>&copy; {{ current_year }} {{ site_title }}. Built with Flask.</p>
    {% endif %}
</div>
```

`footer_text` is **plain text**. It is rendered with Jinja autoescaping and
**not** as markdown and **not** as HTML, so an admin cannot inject markup into
every page of the site. Multi-line text is allowed and rendered with
`white-space: pre-line` in CSS rather than by injecting `<br>`.

`footer_show_posts` replaces the current `show_footer_posts` context flag for
the "Latest from the blog" column. `show_footer_posts` currently also encodes
"hide the footer posts on /search and /tag/ pages" — that behaviour must be
preserved as an *additional* condition, not replaced by the new setting.

### 4. The Site section in the settings template

Add a `<div class="settings-section">` titled **Site** to
`app/templates/admin/settings.html`, containing:

- A comments toggle (checkbox, labelled).
- A footer text field (textarea, with a character counter and the 300-char
  cap enforced server-side).
- Two footer column checkboxes.

The form posts to `{{ url_for('admin.settings_site') }}` with the CSRF token
and `data-loading` (the admin shell already implements `form[data-loading]`
through `app/static/js/shared/utils.js`).

## Migration

New file `migrations/versions/<rev>_add_site_settings_content_flags.py`:

- `site_settings.comments_enabled` — Boolean, `server_default=sa.true()`,
  `nullable=False`.
- `site_settings.footer_text` — String(300), `server_default=""`, `nullable=False`.
- `site_settings.footer_show_posts` — Boolean, `server_default=sa.true()`, `nullable=False`.
- `site_settings.footer_show_tags` — Boolean, `server_default=sa.true()`, `nullable=False`.

`down_revision = "drop_theme_preset_column"` — the single current head.

The downgrade drops the four columns. Existing rows keep their meaning:
`comments_enabled` defaults to true, so an existing site keeps its comments
after the upgrade.

## Tests

1. **Preview order (unit)** — assert that in the rendered `/admin/settings`
   HTML, the index of the Theme Preview section is **less than** the index of
   the Theme section. Assert with string offsets, not a CSS selector.
2. **Preview visible by default (unit)** — assert the rendered settings page
   contains no `style="display: none;"` on `#theme-preview-section`.
3. **Preview auto-loads (browser, `tests/e2e/`)** — open `/admin/settings`,
   wait for `#theme-preview-container` to contain the sample heading without
   clicking any button; assert no console error.
4. **Preview still honours unsaved selections (browser)** — change the dark
   theme select, press Preview, assert the preview request carried the new
   value (assert on the request payload or the resulting `data-color-scheme`
   attribute and content).
5. **Comments toggle (unit)** — with `comments_enabled = False`, assert
   `GET /post/<slug>` does not contain `<section class="comments"`, and
   `POST /post/<slug>/comments` does not create a `Comment` row and flashes an
   error.
6. **Comments toggle (browser)** — toggle it off in the admin, reload the post,
   assert the comment form is gone; toggle it back on, assert it returns.
7. **Footer text (unit)** — assert the footer renders `footer_text` when set,
   and falls back to the default copyright line when empty.
8. **Footer text is escaped (unit)** — set `footer_text` to
   `<script>alert(1)</script>`; assert the rendered page contains the escaped
   form and no `<script>` element with that content.
9. **Footer columns (unit)** — assert the "Latest from the blog" and
   "Browse by tag" headings are absent when the corresponding flags are off.
10. **Settings route (unit)** — POST to `/admin/settings/site` with a valid
    CSRF token; assert the values persisted and the settings cache was
    invalidated. Assert an invalid payload is rejected without a partial write.
11. **Migration (unit)** — assert the new columns exist after `flask db
    upgrade` and that the downgrade drops them. Follow the existing pattern in
    `tests/test_migration_chain.py`.

## Expected files

- `app/models.py` (SiteSettings columns)
- `app/services/site_settings.py` (new)
- `app/routes/admin/settings.py` (`/admin/settings/site`)
- `app/routes/public/comments.py` (fail-closed gate)
- `app/context_processors.py` (expose `comments_enabled`, `footer_text`, `footer_show_posts`, `footer_show_tags`)
- `app/templates/admin/settings.html` (preview reorder, Site section)
- `app/templates/base.html` (footer text)
- `app/templates/post.html` (comment block conditional)
- `app/static/css/public.css` (`.footer-text`, comment-closed note)
- `migrations/versions/<rev>_add_site_settings_content_flags.py` (new)
- `tests/test_site_settings.py` (new)
- `tests/e2e/test_site_settings.py` (new)

## Acceptance criteria

- [ ] The Theme Preview section renders above the Theme section.
- [ ] The preview is visible on load and shows the currently saved theme without a click.
- [ ] Selecting a different theme and pressing Preview still previews the unsaved selection.
- [ ] The preview does not repaint the admin panel outside the preview container.
- [ ] An admin can switch comments off; the comment block disappears and the public endpoint refuses to create comments.
- [ ] Switching comments back on restores the block and the endpoint.
- [ ] Existing comments remain visible while commenting is closed.
- [ ] An admin can set the footer text; it renders on every public page.
- [ ] Footer text is rendered as escaped text, never as markup.
- [ ] An admin can hide either footer column.
- [ ] Each persisted value has exactly one producer and one settings form.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean; the rendered instance confirms every item.

## Dependencies

None. This phase is the entry point of the series. Phase 05 extends the Site
section created here with the page-menu fields; Phase 06 reads
`comments_enabled` to hide the block.

## Completion

**Status:** Not started.
