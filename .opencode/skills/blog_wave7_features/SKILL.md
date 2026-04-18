---
name: blog_wave7_features
description: "Blog CMS Wave 7+ Features - Static pages, archive, search snippets, JSON-LD, Twitter cards, sitemap, canonical URLs, robots.txt, bulk subscriber resend, session IP binding. Triggers: Page model, archive route, search snippets, JSON-LD schema, Twitter cards, canonical URLs, AI crawler blocking, bulk subscriber resend, session IP binding."
metadata:
  requires: "python>=3.12, flask>=3.1"
  homepage: "https://github.com/sugarwookie/blog"
---

## Static Pages (Page model)

**Model** (`app/models.py`):
- `id`, `title`, `slug` (unique), `body`, `published`, `created_at`, `updated_at`
- `ix_pages_published_slug` index for efficient queries
- `Page.generate_slug()` static method

**Routes**:
- `GET /page/<slug>` - Public page render
- `GET /admin/pages` - List all pages
- `GET/POST /admin/pages/new` - Create page
- `GET/POST /admin/pages/edit/<id>` - Edit page
- `POST /admin/pages/delete/<id>` - Delete page

**Slug generation**: `_generate_unique_slug()` in `app/routes/admin/helpers/slug.py` handles collisions by appending counter suffixes.

## Archive Page (`/archive`)

- Cursor-based pagination with `?cursor=` and `?direction=` params
- Year filtering with `?year=` param
- Returns `archive_data` dict: `{year: {month: [posts]}}`
- `ARCHIVE_PER_PAGE = 200` limit
- Template: `app/templates/archive.html`

## Search Result Highlighting

**Functions** (`app/search.py`):
- `extract_snippet(text, query, context_chars=200)` - ~200 char snippet around query match
- `get_search_snippets(posts, query)` - Generates dict mapping `post_id -> snippet`

**Template** (`search.html`):
- Shows snippet when available: `{% if search_snippets and search_snippets[post.id] %}`
- CSS class: `.post-card-snippet`

## Schema.org JSON-LD

`post.html` outputs `<script type="application/ld+json">` with:
- `@type: Article`, `headline`, `description`, `image`, `datePublished`, `dateModified`, `author`, `publisher`, `url`

## Twitter Card Meta Tags

**Base Template** (`base.html`):
- `twitter:title`, `twitter:description`, `twitter:image` meta tags
- Override with `{% block twitter_title %}`, etc.

## Canonical URLs

**Context Processor** (`app/context_processors.py`):
- `canonical_url: BASE_URL.rstrip("/") + request.path`

**Base Template** (`base.html`):
- `<link rel="canonical" href="{{ canonical_url }}">`

## Sitemap Enhancement

Now includes static pages before posts:
- Pages use `monthly` changefreq and `0.7` priority
- URLs: `/page/{slug}`

## Robots.txt AI Crawler Blocking

Comprehensive disallow list in `robots_txt()` route:
- GPTBot, ChatGPT-User, Claude-Web, anthropic-ai, Google-Extended
- FacebookBot, CCBot, Diffbot, DuckDuckBot, ia_aggregator
- ImagesiftBot, img2dataset, Kraken, Orbisk, PerplexityBot
- Pileager, Seek, Sitebot, TikTokBot, Turpom, Vercel/Analytics, YouBot, Bytespider
- Also disallows `/admin/` and `/static/uploads/`

## Bulk Subscriber Resend

`POST /admin/subscribers/bulk` with `action=resend`:
- Sends confirmation email only to unconfirmed/unsubscribed subscribers
- Handles `smtplib.SMTPException, OSError` gracefully
- Reports sent/failed counts via flash messages

## Session IP Binding

`admin_required` decorator logs warning if IP changes:
- Compares `request.remote_addr` with stored `ip_address` from `AdminSession`
- Does NOT invalidate session (preserves mobile user experience)
- Security audit trail only