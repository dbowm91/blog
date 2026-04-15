---
name: blog_wave7_features
description: "Blog CMS Wave 7 New Features - Static pages, archive, search snippets, JSON-LD, Twitter cards, sitemap, canonical URLs, robots.txt, bulk resend, session IP binding. Triggers: Page model, archive route, search snippets, JSON-LD schema, Twitter cards, canonical URLs, AI crawler blocking, bulk subscriber resend, session IP binding."
metadata:
  requires: "python>=3.12, flask>=3.1"
  homepage: "https://github.com/sugarwookie/blog"
---

## Wave 7 New Features (Completed 2026-04-15)

### Static Pages (Page model, routes, admin CRUD)

**Model**: `app/models.py` - `Page` class with:
- `id`, `title`, `slug` (unique), `body`, `published`, `created_at`, `updated_at`
- `ix_pages_published_slug` index for efficient queries
- `Page.generate_slug()` static method (delegates to `generate_slug()` utility)

**Public Routes** (`app/routes/public.py`):
- `GET /page/<slug>` - Renders static page via `page.html` template

**Admin Routes** (`app/routes/admin/pages.py`):
- `GET /admin/pages` - List all pages (`pages_list`)
- `GET /admin/pages/new` - Page editor form (`new_page`)
- `POST /admin/pages/new` - Create page (`new_page`)
- `GET /admin/pages/edit/<id>` - Edit page form (`edit_page`)
- `POST /admin/pages/edit/<id>` - Update page (`edit_page`)
- `POST /admin/pages/delete/<id>` - Delete page (`delete_page`)

**Admin Templates**:
- `app/templates/admin/pages.html` - List view with status badges
- `app/templates/admin/page_editor.html` - Editor form with live markdown preview

**Page Slug Generation**: Uses `_generate_unique_page_slug()` in `app/routes/admin/pages.py` which handles collisions by appending counter suffixes.

### Archive Page (`/archive`)

**Route** (`app/routes/public.py`):
- `GET /archive` - Chronological post listing grouped by year/month
- Returns `archive_data` dict: `{year: {month: [posts]}}`

**Template**: `app/templates/archive.html`
- Posts grouped by year, then by month
- Shows date, title, and tags for each post
- Uses CSS grid with `.archive-year-heading`, `.archive-month-heading`, `.archive-post`

**CSS Classes** (in `style.css`):
- `.archive-list`, `.archive-year`, `.archive-year-heading`
- `.archive-month`, `.archive-month-heading`, `.archive-posts`
- `.archive-post`, `.archive-post-date`, `.archive-post-title`

### Search Result Highlighting

**Functions** (`app/search.py`):
- `extract_snippet(text, query, context_chars=200)` - Extracts ~200 char snippet around first query match with ellipsis
- `get_search_snippets(posts, query)` - Generates snippets for a list of posts, returns `dict[post_id, snippet]`

**Search Route** (`app/routes/public.py`):
- Imports `get_search_snippets` from `app.search`
- Passes `search_snippets` dict to template

**Template** (`app/templates/search.html`):
- Shows snippet instead of summary when available: `{% if search_snippets and search_snippets[post.id] %}`
- CSS class: `.post-card-snippet` (italic, smaller text)

### Schema.org JSON-LD Markup

**Template** (`app/templates/post.html`):
- `{% block article_schema %}` outputs `<script type="application/ld+json">`
- Schema includes: `@type: Article`, `headline`, `description`, `image`, `datePublished`, `dateModified`, `author`, `publisher`, `url`

**Base Template** (`app/templates/base.html`):
- Has `{% block article_schema %}{% endblock %}` placeholder
- JSON-LD placed after `<link rel="canonical">` in `<head>`

### Twitter Card Enhancements

**Base Template** (`app/templates/base.html`):
- Added `twitter:title`, `twitter:description`, `twitter:image` meta tags
- Block names: `{% block twitter_title %}`, `{% block twitter_description %}`, `{% block twitter_image %}`

**Post Template** (`app/templates/post.html`):
- Populates twitter blocks with post title, description, and image

### Canonical URLs

**Context Processor** (`app/context_processors.py`):
- `inject_config` now includes `canonical_url: BASE_URL.rstrip("/") + request.path`

**Base Template** (`app/templates/base.html`):
- `<link rel="canonical" href="{{ canonical_url }}">`

### Enhanced Sitemap

**Route** (`app/routes/public.py` - `_generate_sitemap()`):
- Now includes static pages before posts
- Pages use `monthly` changefreq and `0.7` priority
- Page URLs: `/page/{slug}`

### Robots.txt AI Crawler Blocking

**Route** (`app/routes/public.py` - `robots_txt()`):
- Comprehensive disallow list for AI crawlers:
  - GPTBot, ChatGPT-User, Claude-Web, anthropic-ai, Google-Extended
  - FacebookBot, CCBot, Diffbot, DuckDuckBot, ia_aggregator
  - ImagesiftBot, img2dataset, Kraken, Orbisk, PerplexityBot
  - Pileager, Seek, Sitebot, TikTokBot, Turpom, Vercel/Analytics, YouBot
  - Bytespider
- Also includes `Disallow: /admin/` and `Disallow: /static/uploads/`

### Bulk Subscriber Resend Confirmation

**Route** (`app/routes/admin/subscribers.py` - `subscribers_bulk()`):
- Action `resend` added alongside `delete` and `export`
- Sends confirmation email only to unconfirmed/unsubscribed subscribers
- Handles `smtplib.SMTPException, OSError` gracefully
- Flash messages report sent/failed counts

**Template** (`app/templates/admin/subscribers.html`):
- Bulk actions bar includes "Resend Confirmation" button

### Session IP Binding Warning

**Decorator** (`app/routes/admin/__init__.py` - `admin_required`):
- On each admin request, compares `request.remote_addr` with stored `ip_address` from `AdminSession`
- Logs warning if mismatch (security audit), does NOT invalidate session
- Preserves mobile user experience (WiFi/cellular switching)

## Models Added in Wave 7

### Page Model
```python
class Page(db.Model):
    __tablename__ = "pages"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(UTCDateTime, default=utc_now)
    updated_at = db.Column(UTCDateTime, default=utc_now, onupdate=utc_now)
    published = db.Column(db.Boolean, default=False)
    __table_args__ = (db.Index("ix_pages_published_slug", "published", "slug"),)
```

## Templates Added in Wave 7

- `app/templates/archive.html` - Chronological archive
- `app/templates/page.html` - Static page render
- `app/templates/admin/pages.html` - Admin page list
- `app/templates/admin/page_editor.html` - Admin page editor

## CSS Classes Added in Wave 7

- `.post-card-snippet` - Search result snippet
- `.archive-list`, `.archive-year`, `.archive-month`, `.archive-posts`, `.archive-post`
- `.status-badge`, `.status-published`, `.status-draft`
- `.post-list-slug`, `.post-list-status`