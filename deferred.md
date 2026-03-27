# Deferred Items

Review of `fullplan.md` implementation — all 19 planned items are complete.
This file documents what was dropped (with rationale) and what could be
considered in the future.

---

## Already Dropped in fullplan.md (with rationale)

These items were explicitly excluded by the plan author. Restated here for
completeness:

| Item | Reason |
|------|--------|
| SQLite-backed rate limiting | Overengineering for a small blog. In-memory is fine. |
| Rate limiting shared across workers | Not needed for single-worker SQLite deployment. |
| Media library pagination | Small blog upload directories don't need pagination. |
| Config validation timing | Current behavior is correct — error at `create_app()` time is appropriate. |
| Favicon 301→302 redirect | 301 caching is actually desirable for favicon. |
| Analytics query optimization | Current approach works fine with timezone-naive datetimes used consistently. |
| Image type detection (BMP) | 4 formats (PNG, JPEG, GIF, WebP) sufficient for a blog. |
| Health check endpoint | Nice-to-have, not actionable priority. |
| Admin activity audit log | Significant scope addition; defer unless needed. |
| Request ID for logging | Low value for single-worker blog. |
| Database backup utility | SQLite can be backed up with `cp` or `sqlite3 .backup`. |

---

## Review Notes

### Items completed with minor deviations from the plan

1. **C7 (Newsletter batch sending)**: The plan suggested a `_connect_smtp()` helper
   for reconnection — this was implemented. However, the `with smtplib.SMTP(...) as server`
   context manager was replaced with manual `try/finally` lifecycle management because
   reassigning `server` inside a `with` block doesn't affect the context manager's exit
   handler. The `_connect_smtp()` helper now handles TLS/auth internally, making the
   reconnection path identical to initial connection.

2. **S5 (Unsubscribe enumeration)**: Added `time.sleep(0.1)` for timing-attack
   mitigation. The plan mentioned this but didn't specify duration. 100ms is enough
   to mask DB lookup timing without noticeably impacting UX.

3. **C5 (Empty slug fallback)**: Also handles whitespace-only input (e.g., `"   "`)
   by checking `return slug if slug else "untitled"` after processing, not just the
   initial empty-string guard.

4. **D1 (Subscriber expiry docs)**: Added both the model docstring and a code comment
   in the unsubscribe route explaining the expiry semantics.

---

## Future Considerations (not in original plan)

None identified during review. The codebase is in good shape for a small single-worker
blog deployment.
