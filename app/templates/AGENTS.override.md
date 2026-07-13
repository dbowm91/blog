# Templates Agent Override

Specialized handling for Jinja2 templates and filters.

## Template Structure

```
app/templates/
├── base.html              # Base template with nav, footer, meta tags
├── _sidebar.html           # Sidebar partial
├── _post_content.html      # Post content with share buttons
├── _error.html             # Error page partial
├── 404.html                # Not found page
├── 500.html                # Internal error page
├── archive.html            # Full archive
├── index.html              # Homepage
├── post.html               # Post view with related posts
├── page.html               # Static page view
├── search.html             # Search results
├── series.html             # Series view
├── tag.html                # Tag archive
├── 429.html                # Rate limit exceeded
├── public_preview.html     # Preview for published posts
├── macros.html             # Jinja macros
├── admin/                  # Admin templates
│   ├── base.html           # Admin base with sidebar layout
│   ├── login.html          # Admin login
│   ├── login_base.html     # Login page base
│   ├── login_2fa.html      # 2FA verification page
│   ├── 2fa_setup.html      # 2FA setup page
│   ├── 2fa_verify.html     # 2FA verification page
│   ├── disable_2fa.html    # Disable 2FA page
│   ├── backup_codes.html   # Backup codes display
│   ├── dashboard.html      # Dashboard widgets
│   ├── posts.html          # Post management list
│   ├── editor.html         # Post editor (NOT post_edit.html)
│   ├── page_editor.html    # Page editor
│   ├── revisions.html      # Post revision history
│   ├── revision_diff.html  # Revision diff viewer
│   ├── preview.html        # Post preview
│   ├── subscribers.html    # Subscriber management
│   ├── users.html          # User management
│   ├── sessions.html       # Session management
│   ├── media.html          # Media library
│   ├── backup.html         # Backup/restore
│   ├── settings.html       # Theme/settings
│   ├── pages.html          # Static pages management
│   ├── series.html         # Series management
│   ├── series_editor.html  # Series editor
│   ├── series_posts.html   # Series-post relationship editor
│   ├── tags.html           # Tag management
│   ├── comments.html       # Comment moderation
│   ├── analytics.html      # Analytics dashboard
│   ├── audit.html          # Audit log viewer
│   ├── forgot-password.html # Password reset request
│   ├── reset-password.html  # Password reset form
│   ├── _breadcrumbs.html   # Breadcrumb partial
├── public/                 # Public-facing includes
│   └── comments.html       # Comment form partial
└── email/                  # Email templates
    ├── base_email.html     # Email base template
    ├── newsletter.html     # Newsletter email
    ├── confirm.html        # Subscription confirmation
    └── password_reset.html # Password reset email
```

## Template Filters

Defined in `app/filters.py` (lines 11-85):
- `markdown_safe` - Render markdown to HTML with nh3 sanitization
- `reading_time` - Calculate reading time from text content
- `sanitize_css` - Sanitize custom CSS input
- `post_image_url` - Get post image URL with request-level caching
- `post_image_srcset` - Generate srcset for responsive images
- `post_image_avif_url_stub` - Returns None until AVIF encoding is enabled

Note: Jinja2 built-in filters like `truncate`, `format`, `length` are also available.
Note: `custom_css` is a context variable (from `inject_theme()`), not a filter.

## Template Value Caching

To avoid redundant computations, cache filter results in template loops:
```jinja2
{% set rt = post.body | reading_time %}
{% set img = post|post_image_url %}
{% set truncated_desc = post.body | truncate(160) %}
{% set tc = tag_counts.get(tag.id, 0) %}
```
This is especially important for filters with file I/O or string processing.

## Request-Level Image Caching

The `post_image_url` filter uses Flask `g` object for request-level caching:
```python
if not hasattr(g, "_post_image_cache"):
    g._post_image_cache = {}
post_id = id(post)
if post_id in g._post_image_cache:
    return g._post_image_cache[post_id]
path = os.path.join(app.config["UPLOAD_FOLDER"], post.image)
result = post.image if os.path.isfile(path) else None
g._post_image_cache[post_id] = result
return result
```

## Nested Forms

Bulk form uses `form="bulk-form"` attribute on checkboxes to associate without nesting. Never nest `<form>` elements.

## Open Graph Blocks

Override in templates via `{% block og_image %}` and `{% block twitter_image %}`.

## Context Processors

`app/context_processors.py` provides:
- `inject_csrf()` - Injects `csrf_token` and `csp_nonce`
- `inject_config()` - Site config variables (site_title, site_description, author_name, author_role, author_avatar, base_url, current_year, canonical_url)
- `inject_theme()` - Theme settings and `custom_css` variable
- `inject_footer_data()` - Footer links and data
- `inject_show_footer_posts()` - Injects `show_footer_posts` boolean

Note: `site_title` and `site_description` are the correct variable names (NOT `site_name` or `site_tagline`).

## Critical CSS

The `critical.css` file at `app/static/css/critical.css` is loaded in `base.html:22` for above-the-fold content styling.