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
- `post_image_avif_url_stub` - Returns None until AVIF encoding is enabled

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

## See Also
- [Static Assets](frontend/static-assets.md) - JS/CSS
- [App Factory](core/app-factory.md) - Filter registration
