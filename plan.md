# Improvement Plan

## Completed (Verified)

These items were implemented in prior sessions and verified against the current codebase.

| Item | Evidence |
|------|----------|
| Slug regeneration only on title change | `admin.py:223` — conditional on `title != post.title` |
| Newsletter dedup via `newsletter_sent_at` | `scheduler.py:24` — filters `newsletter_sent_at == None` |
| Race condition on first-run user creation | `__init__.py:187-192` — `IntegrityError` handling |
| SMTP connection reuse for newsletter batch | `email.py:56` — single connection |
| Base62 input validation | `base62.py:20-21` — explicit character check |
| Tag count cache (60s TTL) | `public.py:20-38` — monotonic clock cache |
| Lock file cleanup in scheduler | `scheduler.py:43-49` — `os.remove` in finally |
| Delete confirmation (CSP-safe) | `dashboard.html` — `data-confirm` + `main.js` handler |
| Image upload error feedback | `admin.py:56-60` — returns error tuple, callers flash it |
| Remove unsanitized `markdown` filter | Only `markdown_safe_filter` remains at `__init__.py:87` |
| Remove unused `csrf_exempt` decorator | `csrf.py` — no such decorator exists |
| Consolidate `before_request` into single handler | `__init__.py:114` — single function |
| HTTPS default in `config.toml` | `config.toml:23` — `https://localhost:5000` |
| Config validation deferred to `create_app()` | `__init__.py:40-41` — called inside factory |
| Type hints on utility functions | `utils.py`, `base62.py`, `csrf.py`, `rate_limit.py` |
| Dashboard stat cards (views, posts, shares, subscribers) | `dashboard.html:10-29` |
| Trending posts widget (30 days) | `dashboard.html:32-44` |
| Referrer tracking on page views | `models.py:113` — `referrer` column; `public.py:88` — captured |
| Analytics page with date-range filtering | `/admin/analytics` — `admin.py` |
| Share platform distinction (short URL vs click tracking) | `public.py:176` — short URL clicks tracked as `platform="link"`; `main.js:116` — social/copy clicks tracked per-platform |
| Fix `flash-warning` CSS | `style.css` — `.flash-warning` class added |
| Add favicon | `static/img/favicon.svg` — SVG favicon; `<link rel="icon">` in both base templates; `/favicon.ico` redirects to SVG |
| Strip markdown from RSS fallback | `rss.py` — `_strip_markdown()` removes `#`, `**`, backticks, links from body fallback |
| Clean orphaned uploads | `admin.py` — `os.remove()` on image replace/remove in `edit_post()` and `delete_post()` with `FileNotFoundError` guard |
| Draft preview | `admin/preview/<post_id>` route renders `_post_content.html` regardless of published state; "Preview" link in editor |
| Dashboard search/filter | `dashboard.html` — search input (`?q=`) filters by title `ilike`; status dropdown (`?status=published/draft/all`); pagination preserves params |
| Subscriber management | `/admin/subscribers` — list with pagination, filter by confirmed/unconfirmed, per-subscriber delete, CSV export endpoint |
| Live markdown preview | Split editor layout (textarea + preview pane); debounced 300ms rendering via `POST /admin/preview-markdown`; styled to match `.prose` output |
| Draft autosave | `localStorage` save every 5s on input; keys `draft-<post_id>` or `draft-new`; restore prompt on load; cleared on submit |
| Dark/light mode toggle | CSS variables under `[data-theme="light"]`; toggle button in navbar (sun/moon SVG); `localStorage` persistence; defaults to system `prefers-color-scheme` |
| Media library | `/admin/media` — grid view of `static/uploads/`, shows filename/size, copy URL to clipboard, delete with confirmation |
| Tag management | `/admin/tags` — list with post counts, inline rename, create new, delete (removes from all posts) |
| Newsletter test send | `POST /admin/newsletter-test` — sends latest 3 published posts to admin email |
| Bulk post operations | Dashboard checkboxes + "Select All" toggle; bulk publish/unpublish/delete via `POST /admin/bulk`; confirmation dialogs for destructive actions |

---

## Deferred Items

No items deferred — all 14 planned items were implemented.

---

## Potential Future Enhancements

These were not in the original plan but emerged during implementation:

- **Pagination on media library** — currently loads all files; could paginate if uploads grow large
- **Tag slug uniqueness on rename** — `rename_tag()` doesn't check for slug collisions with other tags
- **Autosave indicator** — visual feedback when draft is auto-saved (e.g., "Saved 5s ago")
- **Media library filtering/search** — find files by name
- **Dark mode in preview template** — preview page uses base.html which includes theme toggle; works correctly
- **Subscriber search** — search subscribers by email
- **Per-subscriber newsletter send** — send newsletter to a single subscriber for testing
