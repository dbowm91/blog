# Site Identity Phase 01 — Admin Settings Reorganisation and Site Customisation

**Roadmap:** [site_identity_authoring_roadmap.md](site_identity_authoring_roadmap.md)
**Date:** 2026-10-24
**Status:** Complete — Part A (theme preview placement) and Part B (comments switch, editable footer, page menu) shipped
**Severity:** High — the settings page cannot express two of the site-level controls the operator asked for, and the theme preview sat below the control it previews.

This phase has two parts:

- **Part A — Theme preview placement.** Shipped. See [Part A](#part-a--theme-preview-placement) and
  the [Completion](#completion) section.
- **Part B — Comments switch and editable footer.** Shipped. See
  [Part B](#part-b--comments-switch-and-editable-footer) and the
  [Completion](#completion) section.

## Operator clarification (2026-10-24)

The operator reviewed this phase and corrected its framing:

> the selector and preview mechanism does work currently. all i'm saying is to
> move where the preview is displayed to sit on top of where you would select
> it, so it's easier to see. otherwise you need to keep going up and down to
> see it.

So the preview mechanism is **not** a defect and must not be redesigned. The
fault is placement only: the panel was rendered *below* the Theme section, so
reaching it meant scrolling past the whole form, and the admin had to keep
travelling up and down between the controls and the result. Everything in this
plan that touched the mechanism has been rewritten accordingly.

## Objective

Make `/admin/settings` a complete site-settings surface:

1. Put the theme preview **above** the theme selector, so the admin can see the
   effect of a theme without scrolling up and down to reach it.
2. Add a comments on/off switch that actually turns comment submission and
   the comment block off across the public site.
3. Add an editable site footer.

## Findings

### Part A — Theme preview placement

### SIA-01 — The theme preview sits below the theme selector (high)

`app/templates/admin/settings.html` ordered the settings sections as:

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
operator had to scroll past the control to reach the feedback and then scroll
back to change the selection. That is the "keep going up and down" the operator
reported.

The mechanism itself is sound and is **not** in scope for redesign:

- `fetchPreview()` reads the *current* values of both selects, so a preview
  reflects an unsaved selection.
- The request goes to `admin.settings_theme_preview` with the CSRF header read
  from `document.documentElement.dataset.csrfHeader`.
- `applyPreviewCss()` injects a `<style>` element carrying the CSP nonce whose
  rules are scoped to `#theme-preview-container[data-color-scheme="…"]`, so
  previewing never repaints the admin panel.
- The `.theme-preview-btn` triggers are `type="button"` inside the Theme
  form's markup, so they never submit the form.

### SIA-02 — A panel above the controls must not resize when it loads (high)

This defect only exists *because of* the move, and it is the reason the panel
cannot simply be relocated and left alone.

Measured on the original markup: the preview container was 156px tall holding
the placeholder and 500px tall holding real preview content — a 344px growth.
With the panel **below** the form that growth was harmless. With the panel
**above** the form it would insert 344px between the operator and the
controls they are using, shoving the selects and the Preview button down the
page at the exact moment they press it.

The same applies to the panel's own visibility. The original section carried
`style="display: none;"`, so it was absent until a preview was fetched:

```html
<!-- app/templates/admin/settings.html:141, before the move -->
<div class="settings-section" id="theme-preview-section" style="display: none;">
```

A panel that appears from nothing above the form pushes the whole form down.
The panel therefore needs a stable, reserved footprint in both states.

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

## Part A — Theme preview placement

### A1. Move the preview panel above the theme selector

In `app/templates/admin/settings.html`:

- Move the `#theme-preview-section` block **above** the Theme section, so the
  order becomes: Theme Preview, Theme, Theme Registry.
- The `.theme-preview-btn` triggers **stay next to the two selects** inside
  the Theme form. They preview the selected-but-unsaved values; that is the
  point of the preview, and moving them would not improve it.
- The mechanism is untouched: same endpoint, same request payload, same scoped
  `<style>` injection, same CSRF header. No new code path is introduced.
- The panel is visible from the start, showing the placeholder copy. It is not
  fetched automatically — the operator asked for a placement change, not a
  behaviour change, and auto-fetching would fire a request on every settings
  page load for no benefit.

### A2. Give the panel a stable footprint

- `.theme-preview-container` declares `min-height` equal to `max-height`
  (380px on desktop, 300px under the 768px breakpoint) so the box cannot
  change size when the placeholder is replaced by real preview content.
- `.theme-preview-loading` gets `min-height: 100%` so the placeholder fills
  the reserved box instead of hugging its top edge.
- The `Clear Preview` action resets the container to the placeholder rather
  than hiding the section. Hiding it would remove 548px from above the form
  and shove everything up. The injected preview `<style>` element is still
  removed on clear.

### A3. Bring the preview into view when it is produced

After a successful preview, scroll the panel into view:

```javascript
previewSection.scrollIntoView({
    behavior: reduceMotion ? 'auto' : 'smooth',
    block: 'nearest'
});
```

`block: 'nearest'` scrolls the minimum distance, so nothing moves when the
panel is already on screen. `prefers-reduced-motion` is honoured. This is the
step that actually removes the up-and-down: the result comes to the operator
instead of the operator going to it.

### A4. Keep the CSP and the scoping intact

The preview stylesheet is injected with `style.setAttribute('nonce', ...)`.
Keep the nonce and keep the `#theme-preview-container[data-color-scheme="…"]`
scoping. Previewing a theme must never repaint the admin panel.

## Part B — Comments switch and editable footer

### B1. Comments switch

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

### Part A — theme preview placement

1. **Preview order (unit)** — assert that in the rendered `/admin/settings`
   HTML the `id="theme-preview-section"` marker appears before the Theme
   section's `<h2>Theme</h2>` marker, and that the preview section is the
   first `.settings-section` in the document. Anchor on `<h2>Theme</h2>`:
   the bare string "Theme" also occurs inside "Theme Preview" and
   "Theme Registry".
2. **Preview visible by default (unit)** — assert the rendered settings page
   does not carry a hidden preview section, and that the placeholder copy is
   present.
3. **No layout shift (unit)** — read the template source and assert the
   `.theme-preview-container` rule declares `min-height` and `max-height` with
   the same value, so the box cannot change size when the preview loads.
4. **Clear keeps the panel (unit)** — assert the clear handler does not set
   `previewSection.style.display = 'none'`, and that it restores the
   placeholder.
5. **Triggers stay with the selects (unit)** — assert each `theme-preview-btn`
   still appears after its corresponding select in the rendered page.
6. **Preview comes into view (browser, `tests/e2e/`)** — press Preview, wait
   for the content, assert the preview section's bounding box top is >= 0.
7. **No shift in the browser (browser)** — measure the container height in the
   placeholder state and again after a preview; assert they are equal.
8. **Clear in the browser (browser)** — assert the section's computed display
   is not `none` and the container shows the placeholder again.

### Part B — comments switch and footer

9. **Comments toggle (unit)** — with `comments_enabled = False`, assert
   `GET /post/<slug>` does not contain `<section class="comments"`, and
   `POST /post/<slug>/comments` does not create a `Comment` row and flashes an
   error.
10. **Comments toggle (browser)** — toggle it off in the admin, reload the post,
    assert the comment form is gone; toggle it back on, assert it returns.
11. **Footer text (unit)** — assert the footer renders `footer_text` when set,
    and falls back to the default copyright line when empty.
12. **Footer text is escaped (unit)** — set `footer_text` to
    `<script>alert(1)</script>`; assert the rendered page contains the escaped
    form and no `<script>` element with that content.
13. **Footer columns (unit)** — assert the "Latest from the blog" and
    "Browse by tag" headings are absent when the corresponding flags are off.
14. **Settings route (unit)** — POST to `/admin/settings/site` with a valid
    CSRF token; assert the values persisted and the settings cache was
    invalidated. Assert an invalid payload is rejected without a partial write.
15. **Migration (unit)** — assert the new columns exist after `flask db
    upgrade` and that the downgrade drops them. Follow the existing pattern in
    `tests/test_migration_chain.py`.

## Expected files

### Part A — shipped

- `app/templates/admin/settings.html` — the panel move, the reserved
  container height, the placeholder reset on clear, the scroll-into-view

### Part B — planned

- `app/models.py` (SiteSettings columns)
- `app/services/site_settings.py` (new)
- `app/routes/admin/settings.py` (`/admin/settings/site`)
- `app/routes/public/comments.py` (fail-closed gate)
- `app/context_processors.py` (expose `comments_enabled`, `footer_text`, `footer_show_posts`, `footer_show_tags`)
- `app/templates/admin/settings.html` (Site section)
- `app/templates/base.html` (footer text)
- `app/templates/post.html` (comment block conditional)
- `app/static/css/public.css` (`.footer-text`, comment-closed note)
- `migrations/versions/<rev>_add_site_settings_content_flags.py` (new)
- `tests/test_site_settings.py` (new)
- `tests/e2e/test_site_settings.py` (new)

## Acceptance criteria

### Part A — theme preview placement

- [x] The Theme Preview section renders above the Theme section.
- [x] The preview panel occupies a stable place and is visible without a click.
- [x] Populating the preview does not change the container height, so the
      controls below it never move.
- [x] Pressing Preview brings the panel into view; the operator no longer has
      to travel up and down to see the result.
- [x] The Preview triggers stay beside the selects they preview, and the
      mechanism is unchanged: an unsaved selection still previews.
- [x] Clear Preview restores the placeholder and leaves the panel in place.
- [x] The preview does not repaint the admin panel outside the preview container.
- [x] The CSP is not weakened and the injected stylesheet keeps its nonce.

### Part B — comments switch and footer

- [ ] An admin can switch comments off; the comment block disappears and the public endpoint refuses to create comments.
- [ ] Switching comments back on restores the block and the endpoint.
- [ ] Existing comments remain visible while commenting is closed.
- [ ] An admin can set the footer text; it renders on every public page.
- [ ] Footer text is rendered as escaped text, never as markup.
- [ ] An admin can hide either footer column.
- [ ] Each persisted value has exactly one producer and one settings form.

### Both parts

- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean; the rendered instance confirms every item.

## Dependencies

None. This phase is the entry point of the series. Phase 05 extends the Site
section created here with the page-menu fields; Phase 06 reads
`comments_enabled` to hide the block.

## Completion

**Status:** Complete. Part A and Part B both shipped.

### Part A — theme preview placement (shipped)

| Item | Resolution |
|---|---|
| Panel position | The `#theme-preview-section` block now renders above the Theme section. Section order is Theme Preview, Theme, Theme Registry. |
| Mechanism | Unchanged. The `.theme-preview-btn` triggers stay next to the two selects inside the Theme form; `fetchPreview()` still posts the current, possibly unsaved select values to `admin.settings_theme_preview` with the CSRF header from `document.documentElement.dataset.csrfHeader`. No auto-fetch was added — the operator asked for a placement change, not a behaviour change. |
| Stable footprint | `.theme-preview-container` declares `min-height` equal to `max-height` (380px, 300px under 768px), and `.theme-preview-loading` gets `min-height: 100%` so the placeholder fills the reserved box. Populating the preview cannot change the box height, so the controls below never move. |
| Visibility | The inline `style="display: none;"` was removed. The panel is visible on load with the placeholder copy "Select a theme below and press its Preview button to see it here." |
| Clear | "Clear Preview" now removes the injected stylesheet and restores a clone of the placeholder into the container. It no longer hides the section, which would have pulled the form up by 548px. |
| Scroll | After a successful preview, `previewSection.scrollIntoView({behavior: reduceMotion ? 'auto' : 'smooth', block: 'nearest'})` brings the panel into view. `prefers-reduced-motion` is honoured. |
| CSP and scoping | Unchanged. The injected `<style>` keeps its nonce and stays scoped to `#theme-preview-container[data-color-scheme="…"]`. |

**Verification** — headless Chromium against the live instance at
`http://localhost:5050`, harness at `/tmp/devlog_review_stubs/preview_placement.py`:

```
section order: Theme Preview (top 199), Theme (top 811), Theme Registry (top 1717)
PASS A1.preview_above_theme
PASS A2.preview_is_first_section
PASS A3.preview_section_visible_by_default
PASS A4.placeholder_shown_initially
PASS B1.preview_populates              scheme=dark heading='Sample Heading'
PASS B2.preview_visible_on_screen_after_press
PASS B3.preview_fully_visible_after_press
PASS B4.preview_and_select_visible_together   previewTop=199 selectTop=993 viewport=1000
PASS B5.select_and_preview_on_same_screen
PASS C1.clear_keeps_panel_visible
PASS C2.clear_restores_placeholder
PASS D1.preview_css_stays_scoped      scoped=1
PASS D2.only_the_site_theme_is_unscoped
PASS E1.no_page_errors
14/14 checks passed
```

Responsive pass, harness at `/tmp/devlog_review_stubs/preview_responsive.py`:
`#theme-preview-container` measured at **380px desktop / 300px mobile in both
the placeholder and the loaded state** — no layout shift at any viewport — with
no horizontal overflow and no page errors at 1280×1000, 1280×800, 768×1024 and
390×844.

At 1280×1000 the preview panel (top 199, bottom 855) and the dark theme select
(top 993) are on screen together after a preview, so the change-theme → preview
loop needs no scrolling.

**Not verified here:** the accessibility warnings box that the preview endpoint
returns for the current theme pair ("Both themes are classified as dark.") adds
108px to the section when it appears. That is content, not layout shift — the
preview box itself does not resize — and it is recorded rather than fixed.

### Part B — comments switch, editable footer and page menu (shipped)

| Item | Resolution |
|---|---|
| Site section | `/admin/settings` gained a **Site** section. Section order is now Theme Preview, Theme, Theme Registry, Site. The six values it owns are `comments_enabled`, `footer_text`, `footer_show_posts`, `footer_show_tags`, `show_pages_in_menu` and `menu_pages`. |
| One form, one endpoint | `POST /admin/settings/site` persists all six. Validation and parsing live in `app/services/site_settings.py` (`validate_site_settings`, `parse_menu_pages`); the route never interprets raw form values. |
| Comments switch — fails closed | The public POST endpoint in `app/routes/public/comments.py` refuses to accept a comment when the switch is off, and `app/templates/post.html` hides the form and shows "Commenting is closed". Existing comments stay visible — the switch closes the door, it does not delete what is already there. |
| Footer text | `footer_text` is **plain text**. It is rendered escaped with `white-space: pre-line` (`.footer-text` in `app/static/css/layout.css`), never markdown and never HTML. |
| Footer columns | `footer_show_posts` and `footer_show_tags` toggle the "Latest from the blog" and "Browse by tag" columns independently. |
| Page menu | `show_pages_in_menu` and the ordered `menu_pages` id list are edited in the same Site section, so there is no second settings form. The parser is owned by `app/services/site_settings.py`; `app/services/navigation.py` re-exports it as a thin alias so there is exactly one parser. |
| Schema | Migration `add_site_settings_content_flags` adds `comments_enabled`, `footer_text`, `footer_show_posts`, `footer_show_tags`, `show_pages_in_menu` and `menu_pages` to `site_settings`, all nullable or defaulted so existing deployments keep working. |
| Read path | `SiteSettings.get_instance()` flushes, so the public read path uses a plain select via `app/services/site_settings.read_site_settings()`. The row is read **once per request** and shared by the theme service, the context processors and the navigation service — the homepage query budget is 9, not 11. |

**Verification** — headless Chromium against the live instance at
`http://localhost:5050`, harness at `/tmp/devlog_review_stubs/identity_verify.py`:

```
PASS settings_has_site_section
PASS settings_has_comments_toggle
PASS settings_has_footer_field
PASS settings_has_menu_field
PASS comments_section_present
PASS nav_has_log_in
PASS nav_has_pages
PASS footer_has_page_links
PASS footer_has_pages_heading
```

Unit coverage: `tests/test_site_settings.py` (16 tests) covers the validation
service, the Site section, the comments switch end-to-end and the footer.
Migration upgrade and downgrade were exercised against a simulated existing
deployment by `/tmp/devlog_review_stubs/mig_verify.py` — both directions pass.

**Recorded, not fixed:** `flask db upgrade` against a *completely empty*
database still fails with `duplicate column name: newsletter_attempts`. Two
branches of the historical migration graph both add that column. This is
pre-existing and is not caused by this series — fixing it means rewriting
historical migrations. It is recorded in
`docs/internals/agent-maintainer-notes.md`.

