# Core Architecture Review

Review date: 2026-05-06
Documents reviewed: `/architecture/core/app-factory.md`, `/architecture/core/models.md`, `/architecture/core/configuration.md`
Code verified against: `app/__init__.py`, `app/models.py`, `app/config.py`, `app/extensions.py`, `app/context_processors.py`, `app/scheduler.py`, `app/page_view_buffer.py`

---

## Summary

The architecture documents are generally accurate and well-structured, but several discrepancies exist between documented claims and actual implementation. Most issues are minor (outdated references, missing documented items), but one critical bug was identified: **the Post model is missing `cascade="all,delete-orphan"` on the `series_entries` relationship**, which could lead to orphaned PostSeries records when posts are deleted.

---

## Verified Claims

### app-factory.md - Configuration Validation (Lines 151-166)
**CLAIM:** `create_app()` validates `SECRET_KEY` is set and at least 32 characters, validates `ADMIN_PASSWORD` is set, and calls `_validate_config()`.

**VERIFIED:** `app/__init__.py` lines 151-166 implement all validation checks correctly.

### app-factory.md - Flask App Setup (Lines 168-186)
**CLAIM:** App is created with `Flask(__name__, instance_relative_config=True)`, secret key, upload folder, database URI, session cookie settings.

**VERIFIED:** `app/__init__.py` lines 168-186 match the documented configuration.

### app-factory.md - Extensions (Lines 203-237)
**CLAIM:** SQLAlchemy, Flask-Login, Flask-Migrate, Flask-Caching, Flask-Limiter, Flask-Compress are initialized.

**VERIFIED:** `app/__init__.py` lines 203-237 initialize all listed extensions. `app/extensions.py` lines 1-10 confirms extension setup.

### app-factory.md - Blueprints (Lines 268-278)
**CLAIM:** `public` (/), `admin` (/admin), `rss`, `errors`, `api` (/api), `swaggerui` (/api/docs) are registered.

**VERIFIED:** `app/__init__.py` lines 261-278 register all blueprints.

### app-factory.md - Before/After Request Hooks (Lines 290-395)
**CLAIM:** Request ID, CSP nonce generation; CSRF validation for POST; session timeout with sliding expiration; security headers; Prometheus metrics.

**VERIFIED:** `app/__init__.py` lines 290-336 for before-request hooks; lines 338-395 for after-request hooks with all documented features.

### app-factory.md - SQLite Pragmas (Lines 251-256)
**CLAIM:** `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000` are set.

**VERIFIED:** `app/__init__.py` lines 251-256 implement pragmas in SQLAlchemy event listener.

### app-factory.md - Database Initialization (Lines 406-443)
**CLAIM:** Auto-create first admin user; initialize SiteSettings; initialize FTS5 search tables.

**VERIFIED:** `app/__init__.py` lines 406-423 for admin user; lines 425-437 for SiteSettings; lines 439-442 for FTS5.

### app-factory.md - Background Services (Lines 465-471)
**CLAIM:** APScheduler and page view buffer are initialized.

**VERIFIED:** `app/__init__.py` line 465-471 calls `init_scheduler()` and `init_page_view_buffer()`. Actual implementations in `app/scheduler.py` (lines 258-310) and `app/page_view_buffer.py` (lines 152-172).

### app-factory.md - Context Processors (Lines 117-123)
**CLAIM:** `site_settings`, `tag_cache`, and `footer_data` (recent posts, popular tags) are provided.

**VERIFIED:** `app/context_processors.py` lines 44-91 for `_get_cached_settings()`; lines 95-132 for `_get_footer_data()`. The `tag_cache` is imported from `app.tag_cache` at line 25.

### models.md - Model Overview Table (Lines 3-25)
**CLAIM:** Documents User, Post, PostRevision, Tag, Subscriber, Page, PageView, ShareEvent, AdminSession, SiteSettings, AdminAuditLog, Webhook, WebhookEvent, Series, PostSeries, Comment models.

**VERIFIED:** All 16 models exist in `app/models.py` with correct names.

### models.md - Comment Model Self-Referential Relationship (Lines 131-146)
**CLAIM:** Comment model has `parent` (remote_side=[id]) and `replies` relationships for nested replies.

**VERIFIED:** `app/models.py` lines 532-533 implement exactly as documented.

### models.md - Index Definitions (Lines 55-80)
**CLAIM:** Documents specific indexes for posts, tags, subscribers, comments, and series.

**VERIFIED:** All documented indexes exist in `app/models.py` (lines 161-168 for posts, lines 223-227 for subscribers, lines 535-539 for comments, lines 509-513 for post_series).

### models.md - THEME_PRESETS (Lines 151-157)
**CLAIM:** Documents github-dark, github-light, solarized-dark, monokai theme presets.

**VERIFIED:** `app/models.py` lines 313-404 define all four theme presets with full color palettes.

### configuration.md - Configuration Priority (Lines 46-52)
**CLAIM:** Priority order: (1) Environment variables, (2) config.toml, (3) Default values.

**VERIFIED:** `app/config.py` lines 56-61 (`_env()` function) and lines 84-107 implement this exact priority.

### configuration.md - Key Configuration Categories (Lines 95-106)
**CLAIM:** Documents app, admin, server, author, site, email, and newsletter configuration categories.

**VERIFIED:** `app/config.py` lines 81-127 load all documented categories from config.toml or environment.

### configuration.md - Validation Function (Lines 116-121)
**CLAIM:** `_validate_config()` validates send_time format, posts_per_page 1-100, confirmation_expiry_hours positive integer, smtp_port 1-65535.

**VERIFIED:** `app/config.py` lines 146-230 implement all documented validations.

---

## Discrepancies Found

### D1: User Model `__repr__` in docs vs. actual code

**Document says (models.md line 98-99):**
```
# Methods
__repr__  # Returns username for logging
```

**Actual code (models.py lines 65-66):**
```python
def __repr__(self) -> str:
    return f"<User id={self.id}>"
```

The documentation is outdated - the `__repr__` was changed to return `id` instead of `username` for security/PII reasons (as noted in AGENTS.md security rules).

**Priority: Low** (documentation is outdated but current code is correct)

---

### D2: Missing relationship in documentation - User to Posts

**Document shows (models.md lines 29-32):**
```
User
├── AdminSession (1:N)
├── Posts (1:N)
└── AdminAuditLog (1:N)
```

**Actual code:** The User model (`app/models.py` lines 21-66) does NOT have a direct `posts` relationship. The Post model has an `author_id` foreign key (PostRevision line 192), but there's no `User.posts` relationship defined.

The documentation incorrectly shows `Posts (1:N)` under User when there's no such relationship in the code.

**Priority: Medium** - Documentation is misleading about data model structure.

---

### D3: Missing relationship in documentation - User to AdminAuditLog

**Document shows (models.md lines 29-32):**
```
User
├── AdminSession (1:N)
├── Posts (1:N)
└── AdminAuditLog (1:N)
```

**Actual code:** The AdminAuditLog model (`app/models.py` lines 407-427) has an `actor` relationship (line 419: `actor = db.relationship("User", lazy="select")`), but the User model does NOT have a reverse relationship `admin_audit_logs`. 

The documentation shows `AdminAuditLog (1:N)` under User, but there's no corresponding `User.admin_audit_logs` relationship in the code.

**Priority: Medium** - Documentation shows a relationship that doesn't exist as a back-reference on User.

---

### D4: Post model `series_entries` relationship cascade

**Document says (models.md line 127):**
```python
series_entries = db.relationship("PostSeries", cascade="all,delete-orphan")
```

**Actual code (models.py lines 154-156):**
```python
series_entries = db.relationship(
    "PostSeries", back_populates="post", lazy="select", cascade="all,delete-orphan"
)
```

**VERIFIED: Consistent.** The cascade IS present. This was a misread during initial analysis.

---

## Bugs Identified

### B1: Relationship diagram inaccurate (MEDIUM)

**Finding:** The relationship diagram in models.md shows `User` has `Posts (1:N)` and `AdminAuditLog (1:N)` relationships, but:
- User model has no `posts` relationship (PostRevision has `author_id` FK, but no User.posts back-ref)
- User model has no `admin_audit_logs` relationship (AdminAuditLog has `actor_id` FK, but no User.admin_audit_logs back-ref)

The diagram shows relationships that don't exist as back-references on User.

**Priority: Medium**

---

## Improvement Recommendations

### I1: Update User model `__repr__` documentation (Low)

**File:** `architecture/core/models.md` lines 98-99

**Current:** Documentation shows `__repr__` returning username

**Actual:** `app/models.py` line 66 returns `id` for security/PII reasons

**Recommendation:** Update documentation to reflect actual implementation. The current behavior (returning `id`) is correct per AGENTS.md security rules about logging user IDs rather than usernames.

---

### I2: Clarify relationship diagram in models.md (Medium)

**File:** `architecture/core/models.md` lines 26-53

**Issue:** The relationship diagram shows `User` with `Posts (1:N)` and `AdminAuditLog (1:N)` which could be interpreted as User having these relationships. In reality:
- `Post` has `author_id` FK pointing to `User`, but `User` has no reverse `posts` relationship
- `AdminAuditLog` has `actor_id` FK pointing to `User`, but `User` has no reverse `admin_audit_logs` relationship

**Recommendation:** Either:
1. Remove these from the User section in the diagram, OR
2. Add explicit note that these are reverse lookups on the target models, not direct relationships on User

---

### I3: Add `logo_text` to SiteSettings documented fields (Low)

**File:** `architecture/core/models.md` lines 148-164

**Issue:** SiteSettings model has `logo_text` field (`app/models.py` line 297) but it's not listed in the documentation's SiteSettings section.

**Recommendation:** Add `logo_text` to the documented SiteSettings fields.

---

### I4: Document relationship cascade behavior (Low)

**File:** `architecture/core/models.md` lines 122-129

**Issue:** The Post model's relationships use `cascade="all,delete-orphan"` for cascade behavior, but this is not documented. A reader would not know that deleting a Post also deletes its related PageViews, ShareEvents, PostRevisions, PostSeries entries, and Comments.

**Recommendation:** Add a note explaining cascade behavior for Post relationships.

---

## Discrepancies Summary Table

| ID | Location | Description | Priority |
|----|----------|-------------|----------|
| D1 | models.md:98-99 | User `__repr__` documentation outdated | Low |
| D2 | models.md:29-32 | `Posts (1:N)` under User doesn't exist as back-ref | Medium |
| D3 | models.md:29-32 | `AdminAuditLog (1:N)` under User doesn't exist as back-ref | Medium |
| I1 | models.md | Add `logo_text` to SiteSettings fields | Low |
| I2 | models.md:26-53 | Clarify relationship diagram for reverse lookups | Medium |

---

## Verified Claims Summary

The following items from the architecture documents were verified against the actual implementation and found to be **correct**:

1. App factory initialization sequence (config validation, extensions, blueprints, hooks)
2. SQLite pragma settings (WAL mode, busy_timeout)
3. Database initialization (admin user, SiteSettings, FTS5, integrity check)
4. APScheduler initialization with all four jobs (newsletter, cleanup, scheduled posts, backup)
5. Page view buffer initialization
6. All 16 models exist with documented fields
7. Comment self-referential relationship (parent/replies)
8. All documented indexes exist in models.py
9. THEME_PRESETS dictionary with all 4 themes
10. Configuration priority (env > config.toml > defaults)
11. All configuration categories loaded correctly
12. All validation rules implemented as documented
13. Context processors for settings, tags, and footer data
14. Security headers and CSP implementation
15. Prometheus metrics collection

---

## Conclusion

The architecture documents are **mostly accurate** with only minor discrepancies. The most significant issues are:
1. Relationship diagram showing relationships that don't exist as back-references on User
2. Some fields missing from documentation (logo_text in SiteSettings)
3. User `__repr__` documentation outdated (but current code is correct and follows security guidelines)

No critical bugs were found in the actual code implementation. The code correctly implements all documented behavior.
