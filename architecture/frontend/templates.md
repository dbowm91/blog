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
- `{{ post.date | format_date }}`
- `{{ post.body | markdown }}`
- `{{ tag.name | slugify }}`

## Context Processors

From `app/context_processors.py`:
- `site_settings` - Theme and settings
- `tag_cache` - Cached tag counts
- `footer_data` - Footer links

## See Also
- [Static Assets](frontend/static-assets.md) - JS/CSS
- [App Factory](core/app-factory.md) - Filter registration
