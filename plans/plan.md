# Consolidated Improvement Plan

**Date:** 2026-05-01
**Status:** Completed
**Consolidated From:** multiple source plans

This plan has been fully implemented. All items are completed.

---

## Implementation Notes for Future Agents

### Security Rules
- **Log ID, not Username**: When logging user actions, always use `user.id`. Never log raw objects or usernames.
- **SSRF Validation**: Use `is_safe_webhook_url` BEFORE any `requests.post` call in background tasks.
- **HMAC Comparison**: Always use `hmac.compare_digest()` for tokens.

### Database Rules
- **FTS5 Sync Timing**: Sync FTS index BEFORE `db.session.commit()`. If commit fails, FTS doesn't need rollback because it's a virtual table based on real data (or handle it with a transaction if using FTS5 `content` option).
- **WAL Mode**: Always use `sqlite3.backup()` for backups when WAL mode is enabled to ensure `shm` and `wal` files are handled correctly.

### Frontend Rules
- **Vite Imports**: Use `import.meta.glob` for all dynamic route-based module loading in `main.js`.
- **CSS Precedence**: `vite_asset` handles hashing. Ensure `base.css` is loaded first.

---

## Verification Checklist
1. `pytest tests/ --cov=app` (Goal: 80%+)
2. `npm run build` (Verify dist chunks)
3. `ruff check app/`
4. `mypy app`
5. `flask db upgrade` (Verify migrations)
