# Templates (`app/templates/`)

Jinja2 templates for the blog.

## Directory Structure

```
app/templates/
├── _error.html                  # Error page partial
├── _post_content.html           # Post content partial
├── _sidebar.html                # Public sidebar partial
├── 404.html                     # Not found page
├── 429.html                     # Rate limit page
├── 500.html                     # Server error page
├── archive.html                 # Archive listing
├── base.html                    # Base template
├── index.html                   # Homepage
├── macros.html                  # Jinja macros
├── page.html                    # Static page template
├── post.html                    # Single post template
├── public_preview.html          # Post preview template
├── search.html                  # Search results
├── series.html                  # Series listing
├── tag.html                     # Tag archive
├── admin/                       # Admin templates
│   ├── _breadcrumbs.html
│   ├── _editor_body.html
│   ├── analytics.html
│   ├── audit.html
│   ├── backup.html
│   ├── backup_codes.html
│   ├── base.html
│   ├── comments.html
│   ├── dashboard.html
│   ├── disable_2fa.html
│   ├── editor.html
│   ├── forgot-password.html
│   ├── login_2fa.html
│   ├── login_base.html
│   ├── login.html
│   ├── media.html
│   ├── page_editor.html
│   ├── pages.html
│   ├── preview.html
│   ├── reset-password.html
│   ├── revision_diff.html
│   ├── revisions.html
│   ├── series.html
│   ├── series_editor.html
│   ├── series_posts.html
│   ├── sessions.html
│   ├── settings.html
│   ├── subscribers.html
│   ├── tags.html
│   ├── users.html
│   ├── 2fa_setup.html
│   └── 2fa_verify.html
├── email/                       # Email templates
│   ├── base_email.html
│   ├── confirm.html
│   ├── newsletter.html
│   └── password_reset.html
└── public/                      # Public partials
    └── comments.html
```

## Template Inheritance

There are **3 standalone base templates**, each with its own `<!DOCTYPE html>` and full HTML skeleton. They do NOT extend each other.

```
base.html                              # Standalone public base template
└── root-level public page templates (extends base.html)

admin/base.html                        # Standalone admin base template
└── admin/*.html (extends admin/base.html)

admin/login_base.html                  # Standalone auth pages base template
├── admin/login.html
├── admin/login_2fa.html
├── admin/forgot-password.html
└── admin/reset-password.html

email/base_email.html                  # Standalone email base template
├── email/confirm.html
├── email/newsletter.html
└── email/password_reset.html
```

> **⚠️ Critical Architectural Detail:** `admin/base.html` and
> `admin/login_base.html` are **standalone templates** — they do NOT
> extend `base.html`. Each has its own complete `<!DOCTYPE html>`,
> `<head>`, and asset tags. This creates triple duplication of HTML
> boilerplate across `base.html`, `admin/base.html`, and
> `admin/login_base.html`. When modifying global `<head>` elements
> (meta tags, CSS links, etc.), all three templates must be updated
> independently. A shared partial or macro would reduce this maintenance
> burden.

### Login Template Asset Loading

`admin/login_base.html` uses `vite_asset()` for CSS and JS assets, enabling CDN prefix support and content hashing just like other templates. This ensures consistent asset loading across all admin templates.

## Filters

Registered in `app/filters.py`:
- `markdown_safe` - Render markdown to HTML with nh3 sanitization, via `render_markdown()` in `app/markdown_renderer.py`. That helper is the single markdown producer: the admin preview endpoint and the feed renderers call it too, and it wraps every code line in `<span class="code-line">` so the stylesheet can number code blocks with a CSS counter.
- `reading_time` - Calculate reading time from text content
- `sanitize_css` - Sanitize custom CSS input
- `post_image_url` - Get post image URL with `storage.exists()` check (returns None if file missing) and request-level caching via `g._post_image_cache`. **Returns a URL, not a filename**: `/static/uploads/<file>` for the local backend and an absolute `https://…` URL for S3. Templates must use the output directly — wrapping it in `url_for('static', filename='uploads/' + img)` produces `/static/uploads//static/uploads/<file>`, which 404s.
- `post_image_srcset` - Generate srcset for responsive images. Checks for variants at 400, 800, and 1200 widths (`{width}_{filename}`), builds `srcset` attribute string with width descriptors (e.g., `400w, 800w, 1200w`). Uses request-level caching via `g._post_image_cache`. Returns `None` if no variants are found. **The attribute must be guarded** — Jinja renders `None` as the literal string `"None"`, and a `srcset` candidate list overrides `src` entirely.
- `post_image_avif_url_stub` - DEPRECATED — always returns `None`. No templates currently use it.

## Context Processors

From `app/context_processors.py`:
- `inject_csrf()` - `csrf_token`, `csrf_header_name`, and `csp_nonce` for forms.
  `csrf_token` is a **string**, not a callable — `{{ csrf_token() }}` raises `TypeError`
  and 500s the page. `csrf_header_name` is the single source of truth for the HTTP
  header that carries the token (`X-CSRF-Token`); it reaches the browser as
  `data-csrf-header` on the root element so client code never hard-codes it.

- `inject_config()` - Site config variables:
  - `site_title` (not site_name)
  - `site_description` (not site_tagline)
  - `author_name`, `author_role`, `author_avatar`
  - `base_url`, `current_year`, `canonical_url`
- `inject_theme()` - Theme settings via centralized `ThemeService` (dark/light CSS variables, scheme, custom CSS)
- `inject_footer_data()` - Footer links and data
- `inject_show_footer_posts()` - `show_footer_posts` boolean (hides footer posts on search/tag pages)

## Cache Invalidation

From `app/context_processors.py`:
- `invalidate_settings_cache()` - Invalidates the SiteSettings cache
- `invalidate_footer_cache()` - Invalidates the footer data memoization cache

## Template Partials

### `prefetch.js`
Intelligent link prefetching that observes link visibility via IntersectionObserver. Prefetches pages when links enter the viewport with configurable delay. Uses `rel="prefetch"` for Chromium-based browsers and falls back to `fetch()` for others.

### `macros.html`
Reusable Jinja2 macros:
- `paginate(pagination)` — Renders pagination controls with page numbers, prev/next links
- `field_error(field)` — Renders inline validation error messages for form fields

### `_post_content.html`
Post content partial with:
- Post hero section (title, date, tags, reading time)
- Share bar (social sharing buttons)
- TL;DR summary block
- Markdown body content

### `_error.html`
Error page partial used by `404.html`, `429.html`, and `500.html`. Renders error code, message, and back link.

### `admin/_editor_body.html`
The `markdown_editor` macro renders the whole markdown body field for both admin editors: the undo/redo buttons, the formatting toolbar, the full-width textarea, the collapsible live preview and the word/character counter. `admin/editor.html` and `admin/page_editor.html` both call it, so the two editors cannot drift apart. The preview sits **below** the textarea and is collapsed through `#toggle-preview-btn`, which is the single owner of the `preview-visible` / `preview-hidden` classes and of `aria-expanded`. The undo and redo buttons carry `data-history-action`, are disabled when there is nothing to undo or redo, and are driven by `app/static/js/admin/editor-history.js`.

### `_sidebar.html`
Admin sidebar partial with navigation links to dashboard sections (posts, pages, media, subscribers, tags, series, settings, audit, backup).

### `data-prism-js-url` Attribute

The `<html>` element in `base.html`, `admin/base.html` and `admin/login_base.html` carries a `data-prism-js-url` attribute set to the Vite-resolved URL of the Prism entry chunk:

```html
<html lang="en" data-prism-js-url="{{ vite_asset('js/prism.js') }}" ...>
```

`loadPrismIfNeeded()` in `main.js` reads the attribute and injects **one** module script, but only when the page actually contains code blocks — it looks for `pre[class*="language-"]` and returns early when there are none. The Prism core, the 18 grammars and the highlighting call all live in that single chunk, so there is no separate grammar script and no dynamic stylesheet injection: the templates link `css/prism.css` directly (`base.html` loads it with the same `media="print"` / `onload` pattern as the other stylesheets, plus a plain link inside `<noscript>`; the admin templates link it plainly).

### The Placeholder Image Element

Where a post has no cover image, the templates render a placeholder element
rather than an `<img>`:

```html
<span class="post-card-img img-placeholder" role="img" aria-label="{{ post.title }}"></span>
```

The markup lives in `index.html`, `tag.html`, `search.html`, `post.html` (the
related-post thumbnail) and `_post_content.html` (the hero). The element is not
an image because the colour of an `<img>`'s content cannot be changed by CSS:
the placeholder mark is themed, and the theme supplies the ink. The `role` and
the `aria-label` reproduce what `alt` gave the old image. See
[Static Assets](static-assets.md#the-post-placeholder).

The social preview metadata (`og:image`, `twitter:image`) and the newsletter
cover point at `/static/img/default-post-social.png`, a self-contained raster,
because a social platform and a mail client render neither an SVG nor a theme.

### `_breadcrumbs.html`
Admin breadcrumb navigation partial for nested admin pages.

## Admin Settings Page Layout

`admin/settings.html` lays its sections out in a fixed order: **Theme Preview**,
then **Theme**, then **Theme Registry**. The preview panel is the first thing
on the page and is always visible — it holds a placeholder until a preview is
fetched, so its presence is not a signal that a preview is running.

The order is a contract, not an arrangement, and four invariants keep it
working:

- The `.theme-preview-btn` triggers stay beside the two theme `<select>`
  controls in the Theme section. `fetchPreview()` reads the current, possibly
  unsaved, select values and posts them to `admin.settings_theme_preview`.
- `.theme-preview-container` sets `min-height` equal to `max-height` (380px,
  300px under the 768px breakpoint), so swapping the placeholder for preview
  content cannot change the box height and move the controls below it.
- "Clear Preview" restores the placeholder; it does not hide the section.
- The stylesheet injected by `applyPreviewCss()` is scoped to
  `#theme-preview-container[data-color-scheme="…"]`, so a preview never
  repaints the rest of the admin panel.

All preview CSS is inline in the template's `<style nonce="{{ csp_nonce }}">`
block. The reasoning behind the placement is recorded in
[Agent Maintainer Notes](../../docs/internals/agent-maintainer-notes.md#admin-theme-preview-placement-2026-10-24).

## See Also
- [Static Assets](static-assets.md) - JS/CSS
- [App Factory](../core/app-factory.md) - Filter registration
