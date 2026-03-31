# Consolidated Improvement Plan

Merged from plan2.md and plan3.md. Items verified against codebase as of 2026-03-31. Organized into parallelizable waves.

---

## Wave 1: Trivial Cleanup (Independent, Zero Risk)

These changes are single-line or small deletions with no dependencies. All can be done in parallel.

### 1.1: Remove dead `id_list` variable

**File**: `app/routes/public.py:145`

`id_list = ",".join(str(i) for i in post_ids)` is computed but never used. The ordering at line 149 builds its own inline string.

**Fix**: Delete line 145.

---

### 1.2: Remove unused `pygments` dependency

**File**: `requirements.txt:7`

`pygments>=2.19.2` is never imported anywhere in the codebase. Prism.js handles syntax highlighting.

**Fix**: Delete line 7 from `requirements.txt`.

---

### 1.3: Move `import markdown` to module level

**File**: `app/__init__.py:97`

`import markdown` is inside the `markdown_safe_filter` function body, running on every filter call. Move it to module level inside `create_app()` alongside `import nh3`.

**Fix**: Add `import markdown` at line 92 (alongside `import nh3`), remove the local import at line 97.

---

### 1.4: Fix `IOError` → `OSError` in scheduler lock handling

**File**: `app/scheduler.py:24` and `app/scheduler.py:89`

`fcntl.flock()` raises `BlockingIOError` (subclass of `OSError`). While `IOError` is currently an alias in Python 3, `OSError` is more correct and future-proof.

**Fix**: Change both `except IOError:` to `except OSError:`.

---

### 1.5: Remove dead `instance_path` config lookup in backup.py

**File**: `backup.py:24-35`

`_config.get("app", {}).get("instance_path", "instance")` reads a config key that doesn't exist in `config.toml`. The fallback `"instance"` is always used.

**Fix**: Simplify `get_db_path()` to just return `os.path.join("instance", "blog.db")`. Remove the `sys.path` manipulation, `from app.config import _config` import, and the `sys` import (only used for path manipulation).

---

### 1.6: Add `server_default` to `newsletter_attempts` migration

**File**: `migrations/versions/89a922eae517_add_newsletter_attempts_and_optimize_.py:26`

`newsletter_attempts` is added as `nullable=False` without a `server_default`. On existing databases with rows, this will fail.

**Fix**: Change line 26 to include `server_default='0'`:
```python
batch_op.add_column(sa.Column('newsletter_attempts', sa.Integer(), nullable=False, server_default='0'))
```

---

### 1.7: Use UTC for media file modification times

**File**: `app/routes/admin.py:603` and `app/routes/admin.py:899`

`datetime.fromtimestamp(stat.st_mtime)` uses local timezone. Inconsistent with `UTCDateTime` TypeDecorator used throughout the app.

**Fix**: Change to `datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)`. Update the import on line 15 from `from datetime import datetime, timedelta` to `from datetime import datetime, timedelta, timezone`.

---

## Wave 2: Security & Robustness (Independent, Low Risk)

### 2.1: Add missing `X-XSS-Protection` security header

**File**: `app/__init__.py:140-160`

The `set_security_headers` handler is documented as setting `X-XSS-Protection: 1; mode=block` but the header is absent. While modern browsers ignore this header (CSP is the modern replacement), the code/docs mismatch should be resolved.

**Fix**: Add `response.headers["X-XSS-Protection"] = "1; mode=block"` in `set_security_headers()`.

---

### 2.2: Harden FTS5 search ordering (SQL injection-adjacent)

**File**: `app/routes/public.py:149`

The search results ordering uses a raw SQL CASE expression built from FTS5 result IDs:
```python
.order_by(db.text(f"CASE posts.id { ' '.join(f'WHEN {i} THEN {n}' for n, i in enumerate(post_ids)) } END"))
```

The `post_ids` come from FTS5 results (integers from `rowid`), so this is safe in practice. However, it constructs raw SQL from data, which is a code smell.

**Fix**: Add a type assertion before building the SQL to document the safety invariant:
```python
assert all(isinstance(i, int) for i in post_ids)
```

---

## Wave 3: SQLAlchemy 2.0 Migration (Largest, Can Be Parallelized by File)

**Rationale:** SQLAlchemy 2.0 deprecates the `Model.query` pattern. The project already uses `db.session.get(Model, id)` for single-object lookups. All remaining `Model.query.*` and `db.session.query()` calls should be migrated for consistency and forward compatibility.

**Total: ~51 occurrences** across 6 files. Each file can be migrated independently. Run full test suite after each file.

### Migration Patterns Reference

| Old Pattern | New Pattern |
|-------------|-------------|
| `Model.query.filter(...).first()` | `db.session.execute(select(Model).filter(...)).scalar_one_or_none()` |
| `Model.query.filter_by(...).all()` | `db.session.execute(select(Model).filter_by(...)).scalars().all()` |
| `Model.query.order_by(...).all()` | `db.session.execute(select(Model).order_by(...)).scalars().all()` |
| `Model.query.filter(...).delete()` | `db.session.execute(delete(Model).where(...))` |
| `Model.query.options(joinedload(...)).filter(...).all()` | `db.session.execute(select(Model).options(joinedload(...)).filter(...)).unique().scalars().all()` |
| `query.paginate()` | `db.paginate(select(...), page=..., per_page=..., error_out=False)` (add `.unique()` for joinedload) |
| `db.session.query(func.count(...)).scalar()` | `db.session.execute(select(func.count(...))).scalar_one()` |
| `db.session.query(Model, func.count(...)).join(...).all()` | `db.session.execute(select(Model, func.count(...).label("count")).join(...)).all()` |
| `Model.query.yield_per(N)` | `db.session.execute(select(Model).execution_options(yield_per=N))` |

### 3.1: `app/routes/admin.py` — 30 occurrences

**`Model.query` calls (14):**

| Line | Current | Target |
|------|---------|--------|
| 71 | `Post.query.filter(Post.slug == slug)` | `db.session.execute(select(Post).filter(Post.slug == slug)).scalar_one_or_none()` |
| 103 | `User.query.filter_by(username=username).first()` | `db.session.execute(select(User).filter_by(username=username)).scalar_one_or_none()` |
| 139 | `Post.query` (dashboard, chained with filters + paginate) | `db.paginate(select(Post).filter(...).order_by(...), page=page, per_page=DASHBOARD_PER_PAGE, error_out=False)` |
| 379 | `Tag.query.filter(Tag.id.in_(ids)).delete(synchronize_session=False)` | `db.session.execute(delete(Tag).where(Tag.id.in_(ids)))` |
| 395 | `Tag.query.filter_by(slug=slug).first()` | `db.session.execute(select(Tag).filter_by(slug=slug)).scalar_one_or_none()` |
| 555 | `Subscriber.query.order_by(...).all()` | `db.session.execute(select(Subscriber).order_by(...)).scalars().all()` |
| 639 | `Tag.query.order_by(Tag.name).all()` | `db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()` |
| 663 | `Tag.query.filter(Tag.slug == slug, Tag.id != tag.id).first()` | `db.session.execute(select(Tag).filter(Tag.slug == slug, Tag.id != tag.id)).scalar_one_or_none()` |
| 701 | `Tag.query.filter_by(slug=slug).first()` | `db.session.execute(select(Tag).filter_by(slug=slug)).scalar_one_or_none()` |
| 719-722 | `Post.query.filter_by(published=True).order_by(...).limit(3).all()` | `db.session.execute(select(Post).filter_by(published=True).order_by(...).limit(3)).scalars().all()` |
| 728 | `User.query.first()` | `db.session.execute(select(User)).scalars().first()` |
| 765 | `Post.query.filter(Post.id.in_(valid_ids)).all()` | `db.session.execute(select(Post).filter(Post.id.in_(valid_ids))).scalars().all()` |
| 814 | `User.query.order_by(User.username).all()` | `db.session.execute(select(User).order_by(User.username)).scalars().all()` |
| 833 | `User.query.filter_by(username=username).first()` | `db.session.execute(select(User).filter_by(username=username)).scalar_one_or_none()` |
| 855 | `User.query.filter_by(is_admin=True).count()` | `db.session.execute(select(func.count(User.id)).filter_by(is_admin=True)).scalar_one()` |

**`db.session.query()` calls (16):**

| Lines | Current | Target |
|-------|---------|--------|
| 182 | `db.session.query(func.count(PageView.id)).scalar() or 0` | `db.session.execute(select(func.count(PageView.id))).scalar_one() or 0` |
| 183 | `db.session.query(func.count(Post.id)).filter(...).scalar() or 0` | `db.session.execute(select(func.count(Post.id)).filter(...)).scalar_one() or 0` |
| 184 | `db.session.query(func.count(ShareEvent.id)).scalar() or 0` | `db.session.execute(select(func.count(ShareEvent.id))).scalar_one() or 0` |
| 185 | `db.session.query(func.count(Subscriber.id)).filter(...).scalar() or 0` | `db.session.execute(select(func.count(Subscriber.id)).filter(...)).scalar_one() or 0` |
| 189-196 | `db.session.query(Post, func.count(...)).join(...).all()` | `db.session.execute(select(Post, func.count(...).label("view_count")).join(...)).all()` |
| 200 | `db.session.query(func.count(Subscriber.id)).filter(...).scalar() or 0` | `db.session.execute(select(func.count(Subscriber.id)).filter(...)).scalar_one() or 0` |
| 372-375 | `db.session.query(Tag.id).outerjoin(...).all()` | `db.session.execute(select(Tag.id).outerjoin(...)).scalars().all()` |
| 413-422 | `db.session.query(func.date(...), func.count(...)).filter(...).all()` | `db.session.execute(select(func.date(...).label("date"), func.count(...).label("views")).filter(...)).all()` |
| 424-426 | `db.session.query(func.count(PageView.id)).filter(...).scalar() or 0` | `db.session.execute(select(func.count(PageView.id)).filter(...)).scalar_one() or 0` |
| 428-436 | `db.session.query(Post, func.count(...)).join(...).all()` | `db.session.execute(select(Post, func.count(...).label("view_count")).join(...)).all()` |
| 441-444 | `db.session.query(ShareEvent.post_id, func.count(...)).filter(...).all()` | `db.session.execute(select(ShareEvent.post_id, func.count(...)).filter(...)).all()` |
| 447-450 | `db.session.query(ShareEvent.platform, func.count(...)).all()` | `db.session.execute(select(ShareEvent.platform, func.count(...).label("count"))).all()` |
| 452-460 | `db.session.query(PageView.referrer, func.count(...)).filter(...).all()` | `db.session.execute(select(PageView.referrer, func.count(...).label("count")).filter(...)).all()` |
| 477 | `db.session.query(func.count(Subscriber.id)).scalar() or 0` | `db.session.execute(select(func.count(Subscriber.id))).scalar_one() or 0` |
| 478 | `db.session.query(func.count(Subscriber.id)).filter(...).scalar() or 0` | `db.session.execute(select(func.count(Subscriber.id)).filter(...)).scalar_one() or 0` |
| 641-643 | `db.session.query(post_tags.c.tag_id, func.count(...)).all()` | `db.session.execute(select(post_tags.c.tag_id, func.count(...).label("cnt"))).all()` |

---

### 3.2: `app/routes/public.py` — 15 occurrences

| Line | Current | Target |
|------|---------|--------|
| 40-48 | `Post.query.options(joinedload(...)).filter(...).all()` | `db.session.execute(select(Post).options(joinedload(...)).filter(...)).unique().scalars().all()` |
| 57-60 | `Post.query.options(joinedload(...)).filter_by(...).paginate(...)` | `db.paginate(select(Post).options(joinedload(...)).filter_by(...), page=page, per_page=POSTS_PER_PAGE, error_out=False).unique()` |
| 62 | `Tag.query.order_by(Tag.name).all()` | `db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()` |
| 75 | `Post.query.filter_by(slug=slug, published=True).first_or_404()` | `db.session.execute(select(Post).filter_by(slug=slug, published=True)).scalar_one_or_none()` + `abort(404)` |
| 110 | `Tag.query.filter_by(slug=slug).first_or_404()` | `db.session.execute(select(Tag).filter_by(slug=slug)).scalar_one_or_none()` + `abort(404)` |
| 113-116 | `Post.query.options(joinedload(...)).filter(...).paginate(...)` | `db.paginate(select(Post).options(joinedload(...)).filter(...), page=page, per_page=POSTS_PER_PAGE, error_out=False).unique()` |
| 119 | `Tag.query.order_by(Tag.name).all()` | Same as line 62 |
| 140 | `Tag.query.order_by(Tag.name).all()` | Same as line 62 |
| 147-150 | `Post.query.options(joinedload(...)).filter(...).order_by(db.text(...)).paginate(...)` | `db.paginate(select(Post).options(joinedload(...)).filter(...).order_by(db.text(...)), page=page, per_page=POSTS_PER_PAGE, error_out=False).unique()` |
| 156-166 | `Post.query.options(joinedload(...)).filter(...).paginate(...)` | Same as line 57 |
| 257 | `Subscriber.query.filter_by(email=email).first()` | `db.session.execute(select(Subscriber).filter_by(email=email)).scalar_one_or_none()` |
| 296 | `Subscriber.query.filter_by(token=token).first()` | `db.session.execute(select(Subscriber).filter_by(token=token)).scalar_one_or_none()` |
| 317 | `Subscriber.query.filter_by(token=token).first()` | `db.session.execute(select(Subscriber).filter_by(token=token)).scalar_one_or_none()` |
| 347 | `Post.query.filter_by(published=True).order_by(...).yield_per(100)` | `db.session.execute(select(Post).filter_by(published=True).order_by(...).execution_options(yield_per=100))` |
| 356 | `Tag.query.yield_per(100)` | `db.session.execute(select(Tag).execution_options(yield_per=100))` |

---

### 3.3: `app/routes/rss.py` — 1 occurrence

| Line | Current | Target |
|------|---------|--------|
| 19-23 | `Post.query.filter_by(published=True).order_by(...).limit(20).all()` | `db.session.execute(select(Post).filter_by(published=True).order_by(...).limit(20)).scalars().all()` |

---

### 3.4: `app/__init__.py` — 1 occurrence

| Line | Current | Target |
|------|---------|--------|
| 218 | `User.query.filter_by(username=username).first()` | `db.session.execute(select(User).filter_by(username=username)).scalar_one_or_none()` |

---

### 3.5: `app/scheduler.py` — 3 occurrences

| Line | Current | Target |
|------|---------|--------|
| 38-45 | `Post.query.filter(...).order_by(...).all()` | `db.session.execute(select(Post).filter(...).order_by(...)).scalars().all()` |
| 51-53 | `Subscriber.query.filter_by(...).filter(...).all()` | `db.session.execute(select(Subscriber).filter_by(...).filter(...)).scalars().all()` |
| 100-104 | `Subscriber.query.filter(...).all()` | `db.session.execute(select(Subscriber).filter(...)).scalars().all()` |

---

### 3.6: `app/cache.py` — 1 occurrence

| Line | Current | Target |
|------|---------|--------|
| 41-46 | `db.session.query(post_tags.c.tag_id, func.count(...)).join(...).all()` | `db.session.execute(select(post_tags.c.tag_id, func.count(...).label("cnt")).join(...)).all()` |

---

### 3.7: Test files — ~12 occurrences (lower priority)

Tests can be migrated incrementally after all app code is done. Focus on app code first.

---

## Wave 4: Deferred / Monitoring Only

### 4.1: Page View Optimization

Every unique post visit triggers an individual `db.session.commit()`. Under traffic, this creates many small transactions.

**Status**: Deferred. SQLite handles small transactions well, and page views are low-frequency for a personal blog. If traffic grows, consider batching via `after_request` handler as a future optimization.

---

## Execution Order & Parallelization

```
Wave 1 (Trivial Cleanup) ── 7 items, all independent, can be done in parallel
Wave 2 (Security & Robustness) ── 2 items, independent, can be done in parallel
Wave 3 (SQLAlchemy 2.0 Migration) ── 6 files, each file independent, can be done in parallel
Wave 4 (Deferred) ── monitoring only, no changes
```

Waves are independent of each other and can be executed in any order. Within each wave, all items are parallelizable.

## Testing Strategy

After each wave (or individual file for Wave 3):
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

Wave 3 requires particular attention — run the full test suite after each file is migrated.

## Files Modified by Wave

| Wave | Files |
|------|-------|
| 1 | `app/routes/public.py`, `requirements.txt`, `app/__init__.py`, `app/scheduler.py`, `backup.py`, `migrations/versions/89a922eae517_*.py`, `app/routes/admin.py` |
| 2 | `app/__init__.py`, `app/routes/public.py` |
| 3 | `app/routes/admin.py`, `app/routes/public.py`, `app/routes/rss.py`, `app/__init__.py`, `app/scheduler.py`, `app/cache.py`, test files |
| 4 | (no changes) |
