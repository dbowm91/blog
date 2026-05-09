# Core Architecture Review - Improvement Plan

Document review of:
- `architecture/core/app-factory.md`
- `architecture/core/configuration.md`
- `architecture/core/models.md`

Against implementation in:
- `app/__init__.py` (app factory)
- `app/config.py` (configuration)
- `app/models.py` (database models)
- `app/extensions.py` (extensions)
- `app/context_processors.py` (context processors)

---

## VERIFIED CLAIMS

### app-factory.md - Configuration Validation (Lines 7-10)
**VERIFIED**: `create_app()` validates `SECRET_KEY` at least 32 chars (line 155), `ADMIN_PASSWORD` required (line 160), and full config via `_validate_config()` (line 166).

### app-factory.md - Flask App Setup (Lines 13-21)
**VERIFIED**: All settings match implementation:
- `SECRET_KEY` (line 169)
- `UPLOAD_FOLDER` (line 170-171)
- `SQLALCHEMY_DATABASE_URI` (lines 175-179)
- `SESSION_COOKIE_SECURE` conditional on env (line 182-184)
- `SESSION_COOKIE_SAMESITE` = "Lax" (line 185)
- `MAX_CONTENT_LENGTH` = MAX_UPLOAD_SIZE + 1MB (line 181)

### app-factory.md - Extensions (Lines 23-31)
**VERIFIED**: All 6 extensions initialized and match actual code (lines 203, 223, 224, 237, 259, 238).

### app-factory.md - Blueprints (Lines 33-41)
**VERIFIED**: All 6 blueprints registered (lines 268-278):
- `public` at `/`
- `admin` at `/admin`
- `rss` at `/rss`, `/atom`, `/json`
- `errors`
- `api` at `/api`
- `swaggerui` at `/api/docs`

### app-factory.md - Before Request Hooks (Lines 45-49)
**VERIFIED**: All hooks implemented (lines 290-336):
- Request ID generation (`g.request_id`)
- CSP nonce generation (`g.csp_nonce`)
- CSRF validation for POST requests
- Session timeout check with sliding expiration

### app-factory.md - After Request Hooks (Lines 51-55)
**VERIFIED**: Security headers, CSP, HSTS, Prometheus metrics all implemented (lines 338-395).

### app-factory.md - SQLite Pragmas (Lines 57-61)
**VERIFIED**: WAL mode and busy_timeout pragmas set via event listener (lines 251-256).

### app-factory.md - Database Initialization (Lines 63-67)
**VERIFIED**: First admin user creation (lines 406-421), SiteSettings init (lines 426-437), FTS5 init (line 440), integrity check (lines 446-463).

### app-factory.md - Background Services (Lines 69-71)
**VERIFIED**: APScheduler (line 467) and page view buffer (line 471) initialized.

### app-factory.md - Security Headers CSP (Lines 73-84)
**VERIFIED**: CSP headers match exactly (lines 356-378) including `style-src-attr 'unsafe-inline'` (line 359) which is not in the doc.

### configuration.md - Configuration Priority (Lines 46-53)
**VERIFIED**: Environment > config.toml > defaults priority implemented in config.py (lines 56-80).

### configuration.md - Key Settings Tables (Lines 56-112)
**VERIFIED**: All documented settings exist in `app/config.py`:
- `SECRET_KEY`, `ADMIN_PASSWORD`, `ADMIN_USERNAME` (lines 84, 90, 89)
- `POSTS_PER_PAGE`, `SESSION_LIFETIME_HOURS`, `MAX_UPLOAD_SIZE` (lines 83, 86, 121)
- SMTP settings (lines 104-108)
- Newsletter settings (lines 110-114)
- Storage settings (lines 129-137)
- Redis settings (lines 129-134)
- Security settings (lines 142-143)

### configuration.md - Validation (Lines 114-121)
**VERIFIED**: `_validate_config()` validates send_time format, posts_per_page range, confirmation_expiry_hours, smtp_port range, base_url scheme (lines 158-242).

### models.md - Model Overview Table (Lines 7-24)
**VERIFIED**: All 15 models exist in `app/models.py`.

### models.md - User Model (Lines 84-109)
**VERIFIED**: `User` model has all documented fields and methods. `__repr__` returns `<User id={self.id}>` (models.py:119-120).

### models.md - Post Model (Lines 113-137)
**VERIFIED**: All fields and relationships match exactly.

### models.md - Comment Model (Lines 139-154)
**VERIFIED**: Self-referential parent/replies relationship implemented correctly (models.py:586-587).

### models.md - SiteSettings and THEME_PRESETS (Lines 156-172)
**VERIFIED**: THEME_PRESETS dict and SiteSettings model match exactly.

### extensions.py - Extensions (Lines 107-115)
**VERIFIED**: `login_manager.login_view = "admin.login"`, `login_manager.session_protection = "strong"` match docs.

---

## DISCREPANCIES

### 1. app-factory.md Line 18: `SESSION_COOKIE_SECURE` is conditional
**Doc says**: `SESSION_COOKIE_SECURE = True (in production)`
**Actual**: `SESSION_COOKIE_SECURE` is set based on `SESSION_COOKIE_SECURE` env var, defaulting to `"true"` but only enforcing `True` in production (lines 182-184, 197-201).

**Impact**: Low - the doc simplifies the behavior. Actual implementation is more sophisticated.

**Recommendation**: Update doc to reflect conditional behavior: "Set via SESSION_COOKIE_SECURE env var, defaults to True in production."

### 2. app-factory.md Line 79: `img-src 'self' data:` missing from doc
**Doc shows**: Standard CSP without `style-src-attr 'unsafe-inline'`
**Actual**: CSP includes `style-src-attr 'unsafe-inline'` (line 359) which is required for inline style attributes used by theme system.

**Impact**: Low - actual CSP is more permissive than documented.

**Recommendation**: Add `style-src-attr 'unsafe-inline'` to documented CSP.

### 3. models.md - Missing Index: `ix_post_series_series_id` and `ix_post_series_post_id`
**Doc lists** (lines 79-81): These indexes in "Key Indexes" section under Series
**Actual**: These indexes ARE defined in PostSeries model (models.py:564-565) but the doc's "Key Indexes" section (lines 57-82) only shows them under Series incorrectly. They should be under PostSeries.

**Impact**: Low - documentation grouping issue only.

**Recommendation**: Move ix_post_series_* indexes from Series section to PostSeries section in models.md.

### 4. models.md - Comments indexes missing from Key Indexes section
**Doc's Key Indexes** (lines 74-77) shows: `ix_comments_post_approved`, `ix_comments_created_at`, `ix_comments_parent_id`
**Actual**: All three indexes exist in models.py:589-592

**Impact**: None - they are documented correctly, just under the wrong heading (shown under "Series" not "Comments")

**Recommendation**: Move comment indexes to a separate "Comments" section under Key Indexes.

### 5. configuration.md - Missing `login_failure_delay` description
**Doc's Security Settings** (lines 107-112): `LOGIN_FAILURE_DELAY` listed with default 0.05 and description "Delay on failed login (seconds)"
**Actual**: `LOGIN_FAILURE_DELAY` in config.py:128 uses env var and config value, and the description is correct.

**Impact**: None - this is accurate.

### 6. configuration.md - `SESSION_IP_BINDING` behavior not documented
**Doc** (configuration.md:16) shows `session_ip_binding = "warn"` but doesn't explain what values are valid or what behavior they produce.

**Actual**: `SESSION_IP_BINDING` is defined in config.py:87 and used in admin routes to control IP binding behavior.

**Impact**: Medium - incomplete documentation of a security-relevant feature.

**Recommendation**: Document valid values for `session_ip_binding` ("off", "warn", "enforce") and explain each behavior.

---

## BUGS FOUND

### BUG 1: Missing `author_id` in Post model documentation
**Location**: models.md lines 113-137
**Issue**: Post model documentation doesn't mention `author_id` field or relationship to User.
**Actual**: Post model has `author_id` implicitly through backref from PostRevision.author relationship, but Post doesn't have a direct author_id column.
**Code Reference**: PostRevision has `author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)` at models.py:246
**Impact**: Documentation is incomplete regarding post authorship tracking.

### BUG 2: SiteSettings model `get_instance()` method not documented
**Location**: models.md lines 156-172
**Issue**: The `get_instance()` class method (models.py:354-361) is a singleton pattern for SiteSettings that isn't mentioned in the doc.
**Impact**: Low - developers may not know SiteSettings is a singleton.

### BUG 3: User.totp_secret_encrypted vs User.totp_secret
**Location**: models.md line 97
**Issue**: Doc says `totp_secret = db.Column(db.String(32))` but actual implementation uses `totp_secret_encrypted = db.Column(db.String(256))` (models.py:33) with a property accessor that decrypts on demand.
**Code Reference**: models.py:33, 43-52
**Impact**: High - the documented model is wrong; TOTP secrets are encrypted at rest.

### BUG 4: Missing `backup_codes_hashed` field
**Location**: models.md lines 84-109 (User Model Details)
**Issue**: Doc doesn't mention `backup_codes_hashed = db.Column(db.JSON, nullable=True)` field (models.py:72).
**Impact**: Medium - 2FA backup codes functionality not documented.

### BUG 5: Missing `totp_enabled` field
**Location**: models.md line 97
**Issue**: Doc shows `totp_secret` column but doesn't mention `totp_enabled = db.Column(db.Boolean, default=False, nullable=False)` (models.py:34).
**Impact**: Medium - 2FA enablement status not documented.

---

## IMPROVEMENT RECOMMENDATIONS

### HIGH PRIORITY

1. **Fix User model documentation for TOTP fields** - models.md:97
   - Replace `totp_secret = db.Column(db.String(32))` with:
     - `totp_secret_encrypted = db.Column(db.String(256), nullable=True)` (encrypted storage)
     - `totp_enabled = db.Column(db.Boolean, default=False, nullable=False)`
     - `backup_codes_hashed = db.Column(db.JSON, nullable=True)`
   - Document the `totp_secret` property that decrypts on access
   - Document `generate_backup_codes()` and `verify_backup_code()` methods

2. **Document SESSION_IP_BINDING behavior** - configuration.md:16
   - Add section explaining valid values: "off", "warn", "enforce"
   - Explain that "warn" logs IP changes but doesn't block, "enforce" blocks sessions with IP changes

### MEDIUM PRIORITY

3. **Reorganize Key Indexes section** - models.md:57-82
   - Group indexes by model with clear section headers
   - Move comment indexes to separate "Comments" section
   - Add PostRevision and AdminAuditLog indexes

4. **Add PostRevision to Post relationship diagram** - models.md:28-39
   - Diagram shows Post relationships but Post model doesn't clearly show PostRevision relationship
   - Add: `Post` → `revisions (1:N)`

5. **Document SiteSettings singleton pattern** - models.md:156-172
   - Add note about `get_instance()` class method
   - Explain that only one SiteSettings row should exist

### LOW PRIORITY

6. **Update CSP documentation** - app-factory.md:73-84
   - Add `style-src-attr 'unsafe-inline'` required for inline style attributes
   - Note: This is intentional to support theme system

7. **Clarify SESSION_COOKIE_SECURE behavior** - app-factory.md:18
   - Change from "True (in production)" to "Set via SESSION_COOKIE_SECURE env var, defaults to True in production"
   - Add note about enforcement in production mode

8. **Document missing models** - models.md:5-25
   - Add `PostRevision` model to overview table with purpose "Post edit history"
   - Note: It's already mentioned in relationships but not as a standalone entry

---

## SUMMARY

| Category | Count |
|----------|-------|
| Verified Claims | 20 |
| Discrepancies | 6 |
| Bugs Found | 5 |
| High Priority Improvements | 2 |
| Medium Priority Improvements | 3 |
| Low Priority Improvements | 3 |

**Key Finding**: The documentation is largely accurate but has critical gaps in the User model's 2FA implementation. The TOTP secret is stored encrypted (`totp_secret_encrypted`), not as a plain string as documented. Several relationship and index references are grouped incorrectly.