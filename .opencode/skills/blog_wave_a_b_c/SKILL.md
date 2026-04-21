---
name: blog_wave_a_b_c
description: "Blog CMS Wave A-C Improvements - Security fixes (health endpoint, CSRF rotation, login timing), performance fixes (newsletter O(n) replacement, N+1 queries, memory usage), render-blocking JS defer, route-based code splitting, FTS caching, lazy-load threshold, archive sorting, scheduler 5-min intervals. Triggers: security hardening, CSRF token rotation, constant-time login delay, newsletter performance, bulk operations N+1, tag creation N+1, email retry blocking, memory optimization, defer scripts, JS route splitting, FTS cache, lazy load bug, archive sort, scheduler interval, scroll throttle, redundant query removal."
metadata:
  requires: "python>=3.12, flask>=3.1"
  homepage: "https://github.com/sugarwookie/blog"
---

## Wave A: Quick Security Fixes

### A1: Health Check `last_newsletter_send` Removed

`GET /health` in `app/routes/public.py` no longer exposes `last_newsletter_send` timestamp:
- Only returns `database`, `scheduler`, and `search` status
- Prevents newsletter configuration disclosure

### A2: CSRF Token Rotation on Privilege Changes

`app/routes/admin/users.py` rotates CSRF token after privilege changes in:
- `promote_user()` - user promoted to admin
- `demote_user()` - admin demoted to regular user
- `make_owner()` - ownership transferred
- `change_password()` - password changed

```python
session["csrf_token"] = secrets.token_hex(32)
```

### A3: Constant-Time Login Delay

`app/routes/admin/auth.py` adds 50ms delay on failed login to prevent timing attacks:
```python
flash("Invalid credentials.", "error")
time.sleep(0.05)
```

## Wave B: Critical Performance Fixes

### B1: Newsletter O(n) String Replacement

`app/email.py` `send_newsletter()` uses `%%UNSUB_PLACEHOLDER%%` pattern instead of per-subscriber str.replace():
```python
unsub_placeholder = "%%UNSUB_PLACEHOLDER%%"
# Template uses {unsubscribe_url} placeholder
html = pre_rendered_html.replace(unsub_placeholder, unsub_url)
text = pre_rendered_text.replace(unsub_placeholder, unsub_url)
```
This is O(1) string replacement per subscriber instead of O(n) full-string scan.

### B2: Bulk Operations N+1 Fix

`app/routes/admin/posts.py` `bulk_operations()` uses eager loading to prevent N+1:
```python
from sqlalchemy.orm import joinedload
posts = (
    db.session.execute(
        select(Post).filter(Post.id.in_(valid_ids)).options(joinedload(Post.tags))
    ).scalars().unique().all()
)
```

### B3: Tag Creation N+1 Fix

`app/routes/admin/helpers/tags.py` `_get_or_create_tags()` uses batch query:
```python
slugs = [Tag.generate_slug(name) for name in valid_names]
existing = (
    db.session.execute(select(Tag).filter(Tag.slug.in_(slugs))).scalars().all()
)
existing_by_slug = {tag.slug: tag for tag in existing}
# Then iterate once
```

### B4: Email Retry No Longer Blocking

`app/email.py` `_send_email_with_retry()` removed blocking `time.sleep()` between retries:
- Transient errors don't block scheduler thread
- Next scheduler run handles retry
- Uses reconnection on `SMTPServerDisconnected`

### B5: Newsletter Memory Optimization

`app/scheduler.py` uses `yield_per(100)` for posts query:
```python
posts = (
    db.session.execute(
        select(Post).filter(...).order_by(Post.published_at.desc()).yield_per(100)
    )
    .scalars()
    .all()
)
```

## Wave C: Medium Priority Performance

### C1: Render-Blocking JavaScript Deferred

`app/templates/base.html` and `admin/base.html` use `defer` attribute:
```html
<script defer src="{{ url_for('static', filename='js/prism.min.js') }}"></script>
<script defer src="{{ url_for('static', filename='js/prism-languages.js') }}"></script>
<script defer src="{{ url_for('static', filename='js/main.js') }}"></script>
```

### C2: Route-Based Code Splitting

`app/static/js/main.js` loads only route-specific modules:
```javascript
const ROUTE_MODULES = {
    '/admin/posts': ['./shared/utils.js', './admin/editor.js', ...],
    '/admin/media': ['./shared/utils.js', './upload.js', ...],
    // Public pages get share, lightbox, toc, etc.
};
```
- Admin pages: 6-8 modules
- Public pages: 10+ modules
- Previously all 15 modules loaded on every page

### C6: Archive Template Sort Removed

`app/templates/archive.html` removed redundant `| sort(reverse=True)`:
- Data already sorted by `public.py` route
- Jinja2 sort was re-sorting already-sorted data

### C7: FTS Table Check Cached

`app/search.py` caches FTS table existence check with 5-minute TTL:
```python
_fts_enabled: bool | None = None
_fts_check_time: float = 0
_FTS_CHECK_TTL = 300

def _check_fts_enabled() -> bool:
    global _fts_enabled, _fts_check_time
    # ... check with TTL
```

### C8: Lazy Load Threshold Fixed

`app/static/js/shared/lazy-load.js` changed from `window.innerHeight * 3` to `window.innerHeight`:
```javascript
if (rect.top > window.innerHeight) {  // Was * 3, now * 1
```

## Low Priority Items (L1-L4)

### L1: Redundant Admin User Query

`app/routes/admin/newsletter.py` removed redundant admin user query - uses `current_user` instead.

### L2: Redundant COUNT Query Removed

`app/scheduler.py` no longer runs separate COUNT query before newsletter send.

### L3: Scroll Throttle Adjusted

`app/static/js/shared/utils.js` scroll handler throttle changed from 10ms to 100ms.

### L4: Scheduler Interval Changed

`app/scheduler.py` `publish_scheduled_posts` runs every 5 minutes (`minute="*/5"`) instead of every minute.

## Tests

```bash
cd /home/sugarwookie/projects/blog && source .venv/bin/activate
ADMIN_PASSWORD=test SECRET_KEY=test-test-test-test-test-test-test-test-test python -m pytest tests/ -v
```