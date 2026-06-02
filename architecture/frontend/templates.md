# Templates (`app/templates/`)

Jinja2 templates for the blog.

## Directory Structure

```
app/templates/
├── _error.html                  # Error page partial
├── _post_content.html           # Post content partial
├── _sidebar.html                # Admin sidebar partial
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
└── public/*.html (extends base.html)

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

> **Note:** `admin/base.html` does NOT extend `base.html`. This creates
> triple duplication of the HTML boilerplate (`<!DOCTYPE>`, `<head>`,
> asset tags) across `base.html`, `admin/base.html`, and
> `admin/login_base.html`. A shared partial or macro would reduce this
> maintenance burden.

## Filters

Registered in `app/filters.py`:
- `markdown_safe` - Render markdown to HTML with nh3 sanitization
- `reading_time` - Calculate reading time from text content
- `sanitize_css` - Sanitize custom CSS input
- `post_image_url` - Get post image URL with `storage.exists()` check (returns None if file missing) and request-level caching via `g._post_image_cache`
- `post_image_srcset` - Generate srcset for responsive images. Checks for variants at 400, 800, and 1200 widths (`{width}_{filename}`), builds `srcset` attribute string with width descriptors (e.g., `400w, 800w, 1200w`). Uses request-level caching via `g._post_image_cache`. Returns `None` if no variants found. (app/filters.py:52-76)
- `post_image_avif_url_stub` - DEPRECATED — always returns `None`. No templates currently use it.

## Context Processors

From `app/context_processors.py`:
- `inject_csrf()` - `csrf_token` and `csp_nonce` for forms
- `inject_config()` - Site config variables:
  - `site_title` (not site_name)
  - `site_description` (not site_tagline)
  - `author_name`, `author_role`, `author_avatar`
  - `base_url`, `current_year`, `canonical_url`
- `inject_theme()` - Theme settings and `custom_css` variable
- `inject_footer_data()` - Footer links and data
- `inject_show_footer_posts()` - `show_footer_posts` boolean (hides footer posts on search/tag pages)

## Cache Invalidation

From `app/context_processors.py`:
- `invalidate_settings_cache()` - Invalidates the SiteSettings cache (line 30-32)
- `invalidate_footer_cache()` - Invalidates the footer data memoization cache (line 35-37)

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

### `_sidebar.html`
Admin sidebar partial with navigation links to dashboard sections (posts, pages, media, subscribers, tags, series, settings, audit, backup).

### `data-prism-css-url` Attribute

The `<html>` element in `base.html:2` includes a `data-prism-css-url` attribute set to the Vite-resolved URL for the configured syntax theme CSS:

```html
<html lang="en" data-syntax-theme="{{ syntax_theme or 'okaidia' }}" data-prism-css-url="{{ vite_asset('css/' + syntax_theme + '.css') }}">
```

This attribute is consumed by `main.js:102` in `loadPrismIfNeeded()` to dynamically inject the Prism CSS stylesheet only when code blocks are present on the page. This enables lazy loading of syntax highlighting CSS — the stylesheet is fetched and applied only when needed, avoiding unnecessary CSS overhead on pages without code blocks.

### `_breadcrumbs.html`
Admin breadcrumb navigation partial for nested admin pages.

## See Also
- [Static Assets](frontend/static-assets.md) - JS/CSS
- [App Factory](core/app-factory.md) - Filter registration
