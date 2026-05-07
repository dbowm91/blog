# Templates (`app/templates/`)

Jinja2 templates for the blog.

## Directory Structure

```
app/templates/
├── base.html                    # Base template
├── admin/                       # Admin templates
│   ├── dashboard.html
│   ├── editor.html
│   ├── posts.html
│   ├── settings.html
│   └── ...
├── email/                       # Email templates
│   ├── confirm.html
│   ├── newsletter.html
│   └── password_reset.html
└── public/                      # Public templates
    ├── index.html
    ├── post.html
    ├── tag.html
    ├── search.html
    └── ...
```

## Template Inheritance

```
base.html
├── public/*.html (extends base.html)
└── admin/*.html (extends base.html)
```

## Filters

Registered in `app/filters.py`:
- `markdown_safe` - Render markdown to HTML with nh3 sanitization
- `reading_time` - Calculate reading time from text content
- `sanitize_css` - Sanitize custom CSS input
- `post_image_url` - Get post image URL with request-level caching
- `post_image_srcset` - Generate srcset for responsive images

## Context Processors

From `app/context_processors.py`:
- `inject_config()` - Site config variables (site_name, site_tagline, etc.)
- `inject_theme()` - Theme settings and `custom_css` variable
- `inject_footer_data()` - Footer links and data
- `inject_csrf()` - `csrf_token` and `csp_nonce` for forms
- `inject_show_footer_posts()` - `show_footer_posts` boolean (hides footer posts on search/tag pages)

## See Also
- [Static Assets](frontend/static-assets.md) - JS/CSS
- [App Factory](core/app-factory.md) - Filter registration
