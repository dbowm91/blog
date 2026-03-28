# Deferred Items from plan.md

The following items from plan.md were deferred/skipped:

## HIGH Priority

### #5. Replace in-memory rate limiting with Redis
Requires Redis dependency and configuration. Not implemented.

### #6. Add account lockout after repeated failures
Depends on Redis implementation (#5).

### #7. Wrap delete operations in try/except with rollback
Partially implemented in edit_post (IntegrityError handling), but delete operations 
lack full try/except with rollback.

## MEDIUM Priority

### #9. Add search performance safeguards
- Needs SQLAlchemy execution_options for query timeout
- Would require database index changes
- SQLite FTS5 not implemented

### #13. Rotate subscriber tokens after use
- Would require model migration (add token_version column)
- Creates additional complexity for token management

### #14. Make upload size configurable
- MAX_CONTENT_LENGTH currently hardcoded
- Minor enhancement, can be done later

## LOW Priority

### #16. Admin password mismatch warning
- Would require admin dashboard UI banner
- Requires adding startup flag or state tracking

---

Total completed: 16 items
Total deferred: 7 items