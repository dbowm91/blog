# Consolidated Improvement Plan

Merged from plan2.md and plan3.md. Items verified against codebase as of 2026-03-31. **All items completed 2026-03-31.**

---

## ✅ Wave 1: Trivial Cleanup (Completed)

### 1.1: Remove dead `id_list` variable ✅
**File**: `app/routes/public.py` — Removed unused `id_list` variable.

### 1.2: Remove unused `pygments` dependency ✅
**File**: `requirements.txt` — Removed `pygments>=2.19.2` (Prism.js handles syntax highlighting).

### 1.3: Move `import markdown` to module level ✅
**File**: `app/__init__.py` — Moved import to module level for efficiency.

### 1.4: Fix `IOError` → `OSError` in scheduler lock handling ✅
**File**: `app/scheduler.py` — Changed both `except IOError:` to `except OSError:`.

### 1.5: Remove dead `instance_path` config lookup in backup.py ✅
**File**: `backup.py` — Simplified `get_db_path()` to always return `os.path.join("instance", "blog.db")`.

### 1.6: Add `server_default` to `newsletter_attempts` migration ✅
**File**: `migrations/versions/89a922eae517_*.py` — Added `server_default='0'` to prevent migration failures on existing databases.

### 1.7: Use UTC for media file modification times ✅
**File**: `app/routes/admin.py` — Changed `datetime.fromtimestamp(stat.st_mtime)` to use `tz=timezone.utc`.

---

## ✅ Wave 2: Security & Robustness (Completed)

### 2.1: Add missing `X-XSS-Protection` security header ✅
**File**: `app/__init__.py` — Added `X-XSS-Protection: 1; mode=block` header.

### 2.2: Harden FTS5 search ordering ✅
**File**: `app/routes/public.py` — Added type assertion for FTS5 result IDs.

---

## ✅ Wave 3: SQLAlchemy 2.0 Migration (Completed)

All `Model.query.*` and `db.session.query()` calls migrated to SQLAlchemy 2.0 patterns.

### Migration Patterns Used

| Old Pattern | New Pattern |
|-------------|-------------|
| `Model.query.filter(...).first()` | `db.session.execute(select(Model).filter(...)).scalar_one_or_none()` |
| `Model.query.filter_by(...).all()` | `db.session.execute(select(Model).filter_by(...)).scalars().all()` |
| `Model.query.order_by(...).all()` | `db.session.execute(select(Model).order_by(...)).scalars().all()` |
| `Model.query.filter(...).delete()` | `db.session.execute(delete(Model).where(...))` |
| `query.paginate()` | `db.paginate(select(...), page=..., per_page=..., error_out=False)` |
| `db.session.query(func.count(...)).scalar()` | `db.session.execute(select(func.count(...))).scalar_one()` |

### Files Migrated
- `app/routes/admin.py` (30 occurrences)
- `app/routes/public.py` (15 occurrences)
- `app/routes/rss.py` (1 occurrence)
- `app/__init__.py` (1 occurrence)
- `app/scheduler.py` (3 occurrences)
- `app/cache.py` (1 occurrence)

---

## Wave 4: Deferred / Monitoring Only

### 4.1: Page View Optimization

Every unique post visit triggers an individual `db.session.commit()`. Under traffic, this creates many small transactions.

**Status**: Deferred. SQLite handles small transactions well, and page views are low-frequency for a personal blog. If traffic grows, consider batching via `after_request` handler as a future optimization.

---

## Testing

```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

**All 186 tests pass.**
