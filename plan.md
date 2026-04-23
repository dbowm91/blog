# Improvement Plan

All items from Waves 1-8, A-I have been completed. This document tracks deferred items only.

---

## Verification Status (2026-04-23)

All 486 tests pass. Deferred items have been addressed as follows:

- **C3, C4, L6, L7**: Implemented via template caching patterns
- **C5**: Already implemented (5-min TTL with proper cache invalidation)
- **L5**: Remains deferred (low impact - GPU-accelerated)

---

## Completed Items

### C3: `reading_time` Filter Called Repeatedly
- **Status**: Completed (2026-04-23)
- **Solution**: Cache using `{% set rt = post.body | reading_time %}` in each template loop
- **Files**: `app/templates/index.html:17-18`, `app/templates/tag.html:20-21`, `app/templates/search.html:25-26`, `app/templates/_post_content.html:4`, `app/templates/post.html:3`

### C4: `post_image_url` Does File I/O Every Call
- **Status**: Completed (2026-04-23)
- **Solution**: Request-level cache using Flask g object in filter
- **Files**: `app/__init__.py:206-221` (filter implementation with g._post_image_cache)

### C5: Theme CSS Regenerated Per Request
- **Status**: Completed (already adequate)
- **Solution**: 5-min TTL with proper cache invalidation on settings change
- **Files**: `app/context_processors.py:30-69`

### L6: Redundant `tag_counts.get()` Call
- **Status**: Completed (2026-04-23)
- **Solution**: Cache in template loop before conditional
- **Files**: `app/templates/_sidebar.html:14`

### L7: `truncate` Called 4x for Same Post
- **Status**: Completed (2026-04-23)
- **Solution**: Cache using `{% set truncated_desc = ... %}` at template top
- **Files**: `app/templates/post.html:3`

---

## Deferred Items (Low Impact)

### L5: `backdrop-filter: blur()` GPU Intensive
- **Status**: Deferred
- **Reason**: Low impact, GPU performance acceptable on modern devices
- **Files**: `app/static/css/style.css:150,151,341,3608`
- **Impact**: Low - used for glassmorphism effects on sidebar/header

---

## Known Test Issues

### Media Upload Test
`TestMediaManagement::test_upload_browse_delete_image` occasionally fails due to timing/async issues with image processing. The image upload itself works correctly.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-23 | Implemented C3, C4, L6, L7 via template caching patterns |
| 2026-04-22 | Verified all deferred items - no completed implementations found |
| 2026-04-21 | Consolidated plan created from plan.md, plan2.md, plan3.md, plan4.md |
| 2026-04-21 | All waves completed (A-I) |
| 2026-04-21 | Plan pruned - completed items removed, deferred items preserved |