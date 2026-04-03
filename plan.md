# Consolidated Improvement Plan

> Merged from plan2.md (backend/test fixes) and plan3.md (UI improvements).
> Organized into parallelizable waves for efficient implementation.

---

## Wave 1: Tests + Critical Bugs

*These items are independent and can be parallelized across sub-agents.*

### 1.1 Fix FTS5 Test Database Corruption

**Priority:** Critical | **Source:** plan2 §1.1

**Problem:** 8+ post creation/edit tests and 2 media tests fail with `database disk image is malformed`. The session-scoped `app` fixture creates the FTS5 virtual table once, while function-scoped `db` fixtures create/drop tables in the same SQLite file, corrupting the FTS5 virtual table.

**Root cause:** `init_fts()` runs during app creation (session scope). Each test's `db` fixture calls `create_all()` / `drop_all()` which drops the `posts` table but leaves the `posts_fts` FTS5 virtual table pointing to a now-deleted table.

**Fix:** Add `init_fts()` call after `create_all()` in the `db` fixture:

```python
@pytest.fixture(scope="function")
def db(app):
    with app.app_context():
        _db.session.remove()
        _db.create_all()
        from app.search import init_fts
        init_fts()
        yield _db
        _db.session.remove()
        _db.drop_all()
        _db.session.remove()
```

**Files:** `tests/conftest.py:31-40`
**Risk:** Low (test-only change)

---

### 1.2 Fix `test_session_cookie_security_flags` — `cookie_jar` Attribute

**Priority:** Critical | **Source:** plan2 §1.2

**Problem:** `tests/test_multi_user.py:118` calls `list(client.cookie_jar())` but `FlaskClient` has no `cookie_jar` attribute. Always fails with `AttributeError`.

**Fix:** Use `response.headers.getlist('Set-Cookie')` to inspect cookies:

```python
def test_session_cookie_security_flags(app):
    client = app.test_client()
    response = client.get("/admin/login")
    cookies = response.headers.getlist("Set-Cookie")
    session_cookie = None
    for cookie_header in cookies:
        if "session" in cookie_header.lower():
            session_cookie = cookie_header
            break
    assert session_cookie is not None
    assert "httponly" in session_cookie.lower()
```

**Files:** `tests/test_multi_user.py:114-128`
**Risk:** Low (test-only change)

---

### 1.3 Fix Multi-User Session Visibility Tests

**Priority:** Critical | **Source:** plan2 §1.3

**Problem:** Tests `test_revoke_other_users_session`, `test_session_isolation_between_users`, and `test_logout_one_user_does_not_affect_other` query `AdminSession` records across app contexts. The sessions created by login via `client.post()` may not be visible to subsequent queries due to session state issues.

**Fix:** Add `_db.session.remove()` before DB queries that check session records to ensure a fresh connection picks up committed data.

**Files:** `tests/test_multi_user.py:157-260`
**Risk:** Low (test-only change)

---

### 1.4 Session Timeout Commit Has No Error Handling

**Priority:** High | **Source:** plan2 §2.1

**Problem:** `app/__init__.py:212-214` — The `before_request` handler deletes an `AdminSession` and commits without try/except. If this fails (e.g., database locked), the user is logged out but the DB transaction may be left inconsistent.

**Fix:** Wrap the delete + commit in try/except:

```python
if admin_session:
    try:
        db.session.delete(admin_session)
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        logger.warning("Failed to delete expired admin session: %s", sid)
```

**Files:** `app/__init__.py:212-214`, add imports for `IntegrityError, OperationalError`
**Risk:** Low (defensive error handling)

---

### 1.5 Error Handlers Query DB Without Protection

**Priority:** High | **Source:** plan2 §2.2

**Problem:** `app/__init__.py:116-148` — Both the 404 and 500 error handlers query `Post` for recent posts. If the database is down (which may have caused the 500), querying it in the error handler raises another exception.

**Fix:** Wrap DB queries in try/except, falling back to empty lists.

**Files:** `app/__init__.py:116-130` (404 handler), `app/__init__.py:132-148` (500 handler)
**Risk:** Low (defensive error handling)

---

### 1.6 `all_sent` Overwritten After SMTP Reconnect

**Priority:** High | **Source:** plan2 §2.3

**Problem:** `app/email.py:133` — After a successful reconnect and retry, `all_sent = True` unconditionally overwrites any previous `False` from earlier failures. If subscriber 1 fails, subscriber 2 disconnects and reconnects successfully, `all_sent` becomes `True` despite subscriber 1's failure.

**Fix:** Remove the `all_sent = True` line after successful retry — only set it to `False` on failure.

**Files:** `app/email.py:131-133`
**Risk:** Low (corrects logic error)

---

### 1.7 Bulk Subscriber Delete Missing Error Handling

**Priority:** High | **Source:** plan2 §2.4

**Problem:** `app/routes/admin/subscribers.py:120-121` — Unlike `delete_subscriber()` (which has try/except), the bulk delete action has no error handling around `db.session.commit()`.

**Fix:** Wrap in try/except like the single delete path.

**Files:** `app/routes/admin/subscribers.py:118-122`
**Risk:** Low (defensive error handling)

---

### 1.8 Newsletter Test Picks First User, Not Admin

**Priority:** Medium | **Source:** plan2 §2.5

**Problem:** `app/routes/admin/newsletter.py:37` — `db.session.execute(select(User)).scalars().first()` returns the first user by ID. The variable `admin_user` is assigned but never used — the check is dead code.

**Fix:** Either remove the dead code or filter by `is_admin=True`.

**Files:** `app/routes/admin/newsletter.py:37-40`
**Risk:** Low (cosmetic/correctness fix)

---

## Wave 2: Code Quality + Accessibility

*Code quality items (backend) and accessibility items (frontend/templates) are independent and can be parallelized.*

### 2.1 FTS LIMIT Uses String Interpolation

**Priority:** Medium | **Source:** plan2 §3.1

**Problem:** `app/search.py:101` — `LIMIT {FTS_RESULT_LIMIT}` is interpolated directly into the SQL string.

**Fix:** Use a parameter:

```python
text(
    "SELECT rowid FROM posts_fts WHERE posts_fts MATCH :q ORDER BY rank LIMIT :limit"
),
{"q": fts_query, "limit": FTS_RESULT_LIMIT},
```

**Files:** `app/search.py:99-104`
**Risk:** Low (defense-in-depth)

---

### 2.2 `_generate_unique_slug()` Max 100 Collisions

**Priority:** Medium | **Source:** plan2 §3.2

**Problem:** `app/routes/admin/helpers.py:226` — If 100 posts share the same base slug, the while loop exits without verifying the 100th slug is unique.

**Fix:** Add a fallback after the loop using a UUID-based suffix.

**Files:** `app/routes/admin/helpers.py:226-238`
**Risk:** Low (edge case handling)

---

### 2.3 `_commit_post_with_rollback()` Retries on Any IntegrityError

**Priority:** Medium | **Source:** plan2 §3.3

**Problem:** `app/routes/admin/posts.py:178-204` — The retry logic triggers on ANY `IntegrityError`, not just slug collisions. A foreign key violation would also trigger a retry with a new slug, which won't fix the underlying issue.

**Fix:** Check if the error is specifically a unique constraint violation on `slug` before retrying:

```python
except IntegrityError as e:
    db.session.rollback()
    if "slug" not in str(e).lower():
        raise  # Re-raise non-slug integrity errors
    # ... existing retry logic
```

**Files:** `app/routes/admin/posts.py:187-204`
**Risk:** Medium (changes error handling behavior)

---

### 2.4 Remove Deprecated `X-XSS-Protection` Header

**Priority:** Low | **Source:** plan2 §3.4

**Problem:** `app/__init__.py:227` — `X-XSS-Protection` is deprecated and ignored by all modern browsers.

**Fix:** Remove the line.

**Files:** `app/__init__.py:227`; update Security Headers section in `AGENTS.md`
**Risk:** None (removes a no-op header)

---

### 2.5 `BASE_URL` Has No Fallback

**Priority:** Medium | **Source:** plan2 §3.5

**Problem:** `app/config.py:87` — `BASE_URL = _config["site"]["base_url"].rstrip("/")` raises `KeyError` at import time if `site.base_url` is missing from `config.toml`.

**Fix:** Use `.get()` with a sensible default:

```python
BASE_URL = _config.get("site", {}).get("base_url", "http://localhost:5000").rstrip("/")
```

**Files:** `app/config.py:87`
**Risk:** Low (prevents import-time crash)

---

### 2.6 `short_url_redirect` Commit Without Error Handling

**Priority:** Medium | **Source:** plan2 §3.6

**Problem:** `app/routes/public.py:259-261` — `ShareEvent` commit has no try/except. If it fails, the redirect still happens but the share event is lost.

**Fix:** Add try/except like `track_share()` does.

**Files:** `app/routes/public.py:259-261`
**Risk:** Low (defensive error handling)

---

### 2.7 Cache `_get_tag_ttl()` Config Import

**Priority:** Low | **Source:** plan2 §4.1

**Problem:** `app/cache.py:21-23` — `_get_tag_ttl()` imports `TAG_CACHE_TTL_SECONDS` from config on every call.

**Fix:** Import at module level since `TAG_CACHE_TTL_SECONDS` is a module-level constant.

**Files:** `app/cache.py:21-23`
**Risk:** None (micro-optimization)

---

### 2.8 Lightbox Focus Management

**Priority:** High | **Source:** plan3 §1.1

**Problem:** The image lightbox (`post.html:125-128`) opens a full-screen overlay but does not trap focus, does not move focus into the lightbox, and does not return focus to the triggering element on close.

**Changes:**
1. Store reference to the element that triggered the lightbox (`document.activeElement`)
2. On open: move focus to the lightbox container or the close button
3. Trap focus inside the lightbox while open (Tab/Shift+Tab cycle)
4. On close: return focus to the stored trigger element
5. Add `role="dialog"`, `aria-modal="true"`, `aria-label` to `#lightbox`

**Files:** `app/templates/post.html`, `app/static/js/main.js`
**Risk:** Low (accessibility improvement)

---

### 2.9 Post Card Redundant Navigation

**Priority:** High | **Source:** plan3 §1.2

**Problem:** Post cards use `role="link"` + `tabindex="0"` on a `<div>` that also contains a nested `<a>` element. Screen readers announce both the card and the link, creating confusing duplicate navigation.

**Fix:** Wrap the entire card content in a single `<a href="...">` element. Remove `role="link"` and `tabindex="0"` from the card `<div>`.

**Files:** `app/templates/index.html`, `app/templates/tag.html`, `app/templates/search.html`, `app/static/js/main.js`
**Risk:** Medium (affects multiple templates and CSS)

---

### 2.10 Heading Anchor Link Positioning

**Priority:** Medium | **Source:** plan3 §1.3

**Problem:** Heading anchor links (`#` icons) are positioned at `left: -24px`, which pushes them off-screen on narrow viewports and breaks completely for RTL languages.

**Changes:**
1. Change positioning to `right: 100%` with `padding-right: 8px`
2. On mobile (below 768px), move anchors to appear inline after the heading text
3. Use `inset-inline-start` for CSS logical properties (RTL support)
4. Ensure anchors are visible on focus (not just hover) for keyboard users

**Files:** `app/static/js/main.js`, `app/static/css/style.css`
**Risk:** Low (CSS/JS only)

---

### 2.11 Flash Message Auto-Dismiss for Screen Readers

**Priority:** Medium | **Source:** plan3 §1.4

**Problem:** Flash messages auto-dismiss after 5 seconds. There is no focus pause for keyboard/screen reader users and no visible close button. The flash container also lacks `role="status"` and `aria-live="polite"`.

**Changes:**
1. Add focus pause: pause timer on `focusin`, resume on `focusout`
2. Add a visible close button (`×`) to each flash message
3. Increase the auto-dismiss timeout from 5s to 8s
4. Add `role="status"` and `aria-live="polite"` to the flash container

**Files:** `app/static/js/main.js`, `app/templates/base.html`, `app/templates/admin/base.html`
**Risk:** Low (accessibility improvement)

---

### 2.12 Reading Time Accessibility

**Priority:** Low | **Source:** plan3 §1.5

**Problem:** The reading time output is a bare `<span>` with no `aria-label` indicating it's a reading time estimate.

**Fix:** Add `aria-label="Estimated reading time"` to the `<span class="reading-time">` elements in all templates.

**Files:** `app/templates/post.html`, `app/templates/index.html`, `app/templates/tag.html`, `app/templates/search.html`, `app/templates/_post_content.html`
**Risk:** None (purely additive)

---

## Wave 3: CSS Cleanup + Admin UX Standardization

*CSS cleanup and admin UX standardization are independent and can be parallelized.*

### 3.1 Remove Duplicate Responsive CSS Rules

**Priority:** Medium | **Source:** plan3 §2.1

**Problem:** `.content-layout` has identical `grid-template-columns: 1fr` and `position: static` rules at both 960px and 768px breakpoints. The 960px rules are entirely redundant.

**Fix:** Audit all `@media (max-width: 960px)` rules and identify which are fully overridden by 768px rules. Remove redundant rules.

**Files:** `app/static/css/style.css`
**Risk:** Medium (CSS changes can affect multiple pages)

---

### 3.2 Standardize Empty State Markup

**Priority:** Medium | **Source:** plan3 §2.2

**Problem:** Empty states use inconsistent markup — some use `<p class="empty-state">` (plain text), others use `<div class="empty-state"><h3>...</h3><p>...</p></div>` (with icon via `::before`).

**Fix:** Define a standard empty state pattern and update all templates:

```html
<div class="empty-state">
  <h3>No items found</h3>
  <p>Description or call to action.</p>
</div>
```

**Files:** All templates with empty states: `dashboard.html`, `subscribers.html`, `tags.html`, `users.html`, `sessions.html`, `media.html`, `backup.html`, `search.html`, `index.html`
**Risk:** Low (CSS already handles both patterns)

---

### 3.3 Standardize Filter Patterns

**Priority:** Medium | **Source:** plan3 §3.1

**Problem:** Three different filter patterns exist across admin pages: Dashboard uses `<select>` with auto-submit via JS, Subscribers uses link-based filter tabs, Analytics uses `<select>` with `data-auto-submit` attribute.

**Fix:** Adopt link-based filter tabs (subscribers pattern) as the standard — they are more accessible (no JS required), show the current state in the URL, and work without JavaScript. Create a reusable `_filter_tabs.html` partial.

**Files:** `app/routes/admin/posts.py`, `app/routes/admin/analytics.py`, `app/templates/admin/dashboard.html`, `app/templates/admin/subscribers.html`, `app/templates/admin/analytics.html`, `app/static/js/main.js`
**Risk:** Medium (affects multiple routes and templates)

---

### 3.4 Standardize Bulk Actions Pattern

**Priority:** Medium | **Source:** plan3 §3.2

**Problem:** Dashboard uses `form="bulk-form"` attribute on checkboxes with actions outside the form. Subscribers wraps bulk actions inside the form. JS handling is duplicated.

**Fix:** Adopt the dashboard pattern (`form="bulk-form"` attribute) as the standard. Create a reusable `_bulk_actions.html` partial. Consolidate bulk select JS into a single handler in `main.js`.

**Files:** `app/templates/admin/dashboard.html`, `app/templates/admin/subscribers.html`, `app/static/js/main.js`
**Risk:** Low (standardization only)

---

### 3.5 Standardize Button Sizing

**Priority:** Low | **Source:** plan3 §3.3

**Problem:** Inconsistent use of `btn-small`, `btn-ghost`, and size classes across admin pages.

**Fix:** Define clear button size conventions and audit all admin templates:
- `btn` — default size, used for primary actions on detail pages
- `btn btn-small` — used in lists, tables, and dense layouts
- `btn btn-small btn-ghost` — used for secondary/destructive actions in lists

**Files:** All admin templates, `app/static/css/style.css`
**Risk:** Low (cosmetic)

---

### 3.6 Add Loading States for Individual Form Submissions

**Priority:** Medium | **Source:** plan3 §3.4

**Problem:** Only bulk operations have a loading overlay. Individual post/tag/user delete operations have no visual feedback during submission.

**Changes:**
1. Add a generic JS handler for forms with `data-loading-overlay` attribute
2. On submit: show a small spinner overlay on the form or button
3. Disable the submit button during submission
4. Guard all new admin JS with `document.body.classList.contains('admin-body')`

**Files:** `app/static/js/main.js`, all admin templates with destructive forms
**Risk:** Low (additive)

---

### 3.7 Animate Admin Nav Dropdown

**Priority:** Low | **Source:** plan3 §3.5

**Problem:** The "More" dropdown in the admin nav uses `display: none/block` with no animation, while the mobile menu uses CSS animations.

**Fix:** Replace `display: none/block` with `opacity` + `visibility` + `transform` for a fade + slide animation.

**Files:** `app/templates/admin/base.html`, `app/static/css/style.css`, `app/static/js/main.js`
**Risk:** Low (cosmetic)

---

## Wave 4: Feature Additions + Minor Polish

*Feature additions and minor polish items can be parallelized.*

### 4.1 Media Library Search/Filter

**Priority:** Medium | **Source:** plan3 §4.1

**Problem:** With many files, the media grid becomes hard to navigate. No search or filter exists.

**Changes:**
1. Add a search input that filters by filename
2. Add filter tabs for file types (Images, Documents, Other)
3. Server-side search for large libraries (query by filename with LIKE)
4. Preserve search/filter state in URL params
5. Add empty state for no results

**Files:** `app/routes/admin/media.py`, `app/templates/admin/media.html`, `app/static/js/main.js`
**Risk:** Low (additive feature)

---

### 4.2 Image Preview in Editor

**Priority:** Medium | **Source:** plan3 §4.2

**Problem:** The cover image upload is a simple file input with no client-side preview until after save.

**Changes:**
1. Add a preview area next to or below the file input
2. On file selection, use `FileReader` to display a preview
3. Show the current image (if editing an existing post) as the default preview
4. Add a "Remove" button to clear the selected image

**Files:** `app/templates/admin/editor.html`, `app/static/js/main.js`
**Risk:** Low (additive feature)

---

### 4.3 Word/Character Count in Editor

**Priority:** Low | **Source:** plan3 §4.3

**Problem:** No word or character count in the editor.

**Changes:**
1. Add a small status bar below the textarea showing word count and character count
2. Update counts on input (debounced to every 500ms)
3. Style to match the draft autosave status indicator

**Files:** `app/templates/admin/editor.html`, `app/static/js/main.js`
**Risk:** Low (additive feature)

---

### 4.4 Interactive Analytics Charts

**Priority:** Low | **Source:** plan3 §4.5

**Problem:** Analytics charts are pure CSS bar charts using inline `style="height: X%"`. The `title` attribute provides basic tooltips but no CSS hover effects or accessible labels.

**Changes:**
1. Add CSS-only tooltips using `data-tooltip` attribute and `::after` pseudo-element
2. Add axis labels (days/months) below the chart bars
3. Add a subtle hover effect on bars
4. Ensure tooltips are accessible (`role="tooltip"` and `aria-describedby`)
5. Keep it CSS-only — avoid adding a charting library dependency

**Files:** `app/templates/admin/analytics.html`, `app/static/css/style.css`
**Risk:** Low (additive)

---

### 4.5 Backup Restore Confirmation Styling

**Priority:** Low | **Source:** plan3 §5.1

**Problem:** The restore action has `data-confirm` but it's a destructive operation that overwrites the database — it could use more prominent warning styling.

**Note:** Requires building a custom confirmation modal to replace the native `confirm()` dialog (which is not stylable). This modal should be reusable for other destructive actions.

**Changes:**
1. Build a custom confirmation modal (reusable, CSP-compliant, focus-trapped)
2. Add a `data-confirm-type="danger"` attribute to the restore button
3. Style danger confirmations with red accents and a more prominent warning message

**Files:** `app/templates/admin/backup.html`, `app/static/js/main.js`, `app/static/css/style.css`
**Risk:** Medium (new modal component)

---

### 4.6 Code Block `lang` Attribute for Screen Readers

**Priority:** Low | **Source:** plan3 §5.2

**Problem:** Prism language classes are present but no `lang` attribute on code blocks for screen readers.

**Fix:** When adding copy buttons to code blocks, also add a `lang` attribute to the `<code>` element based on the language class (e.g., `language-python` → `lang="python"`).

**Files:** `app/static/js/main.js`
**Risk:** None (additive)

---

### 4.7 Document Button Convention in AGENTS.md

**Priority:** Low | **Source:** plan3 §5.3

**Problem:** No documented convention for button sizing and variants.

**Fix:** Add a "Button Conventions" section documenting `btn`, `btn-small`, `btn-primary`, `btn-ghost`, `btn-danger` with examples.

**Files:** `AGENTS.md`
**Risk:** None (documentation only)

---

## Deferred / Explicitly Not Being Changed

- **Rate limiting** — Intentionally absent; handled by reverse proxy (documented in AGENTS.md)
- **FTS exception swallowing** (plan2 §4.2) — Intentional design; LIKE fallback handles stale entries
- **Email `server.quit()` in finally** — Already correct
- **`_save_image()` reading entire file into memory** — Protected by `MAX_CONTENT_LENGTH` Flask config
- **`_cleanup_orphan_tags()` not committing** — Documented pattern; callers are responsible
- **Skeleton loading states** (plan3 §4.4) — Possibly skip; server-rendered app makes this less critical
- **CSS file splitting** (plan3 §2.3) — Optional; only pursue if file grows beyond 4,000 lines

---

## Implementation Order (Waves)

| Wave | Items | Parallelization |
|------|-------|-----------------|
| **Wave 1** | 1.1–1.8 (Tests + Critical Bugs) | All 8 items can be parallelized |
| **Wave 2** | 2.1–2.7 (Code Quality) + 2.8–2.12 (Accessibility) | Backend (2.1–2.7) and Frontend (2.8–2.12) can be parallelized |
| **Wave 3** | 3.1–3.2 (CSS Cleanup) + 3.3–3.7 (Admin UX) | CSS (3.1–3.2) and Admin UX (3.3–3.7) can be parallelized |
| **Wave 4** | 4.1–4.7 (Features + Polish) | All items can be parallelized |

**Dependencies between waves:**
- Wave 2 depends on Wave 1 (tests must be green before code quality changes)
- Wave 3 depends on Wave 2 (accessibility fixes should land before admin UX standardization)
- Wave 4 depends on Wave 3 (features should use standardized patterns)

**Total estimated effort:** ~30–45 hours (excluding deferred items)

---

## Risks & Considerations

- **CSS changes are high-risk** — a single broken rule can affect multiple pages. Test thoroughly across all templates after CSS changes.
- **Accessibility changes require testing** — use a screen reader (VoiceOver, NVDA) to verify improvements. Automated tools (axe, Lighthouse) catch only ~30% of issues.
- **Admin pattern standardization affects multiple routes** — ensure route handlers support the new filter/bulk patterns before updating templates.
- **No external dependencies** — all improvements must use self-hosted assets. Do not add charting libraries, icon libraries, or external fonts.
- **CSP compliance** — all new inline scripts/styles must use `nonce="{{ csp_nonce }}"`. No inline event handlers.
- **SQLite only** — media library search should use LIKE patterns (already the standard for this codebase).
- **Admin JS guard** — all new JavaScript for admin pages must be guarded with `document.body.classList.contains('admin-body')` to prevent firing on public pages.
- **Native `confirm()` replacement** — items 3.6 and 4.5 require a custom confirmation modal to replace the native `confirm()` dialog. Build this modal once and reuse it across both items.
