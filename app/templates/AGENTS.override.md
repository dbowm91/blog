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
├── admin/                  # Admin templates
│   ├── base.html           # Admin base with sidebar layout
│   ├── dashboard.html      # Dashboard widgets
│   ├── posts.html          # Post management
│   ├── post_edit.html      # Post editor
│   ├── subscribers.html    # Subscriber management
│   ├── users.html          # User management
│   ├── sessions.html       # Session management
│   ├── media.html          # Media library
│   ├── backup.html         # Backup/restore
│   ├── settings.html       # Theme settings
│   ├── pages.html          # Static pages
│   ├── series.html         # Series management
│   └── newsletter.html     # Newsletter
├── public/                 # Public page templates
│   ├── index.html          # Homepage
│   ├── post.html           # Post view with related posts
│   ├── page.html           # Static page view
│   ├── tag.html            # Tag archive
│   ├── series.html          # Series view
│   ├── archive.html        # Full archive
│   ├── search.html          # Search results
│   └── subscribe.html      # Subscription confirmation
└── email/                  # Email templates
    └── newsletter.html     # Newsletter email
```

## Template Filters

Defined in `app/filters.py` (lines 11-72):
- `markdown_safe` - Render markdown to HTML with nh3 sanitization
- `reading_time` - Calculate reading time from text content
- `sanitize_css` - Sanitize custom CSS input
- `post_image_url` - Get post image URL with request-level caching
- `post_image_srcset` - Generate srcset for responsive images

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