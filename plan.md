# Improvement Plan

All items from Waves 1-8, A-I have been completed. This document tracks deferred items only.

---

## Verification Status (2026-04-22)

All 486 tests pass. All deferred items below have been verified as truly deferred
with no completed implementations found.

---

## Deferred Items

These items were intentionally skipped due to significant refactoring requirements or minimal impact:

### C3: `reading_time` Filter Called Repeatedly
- **Status**: Deferred (verified)
- **Reason**: Significant refactor needed - filter called 4x per post (index, tag, search templates + post content)
- **Files**: `app/__init__.py:190-197`, `app/templates/index.html:27`, `app/templates/tag.html:31`, `app/templates/search.html:36`, `app/templates/_post_content.html:15`
- **Impact**: Medium - each call parses markdown and counts words

### C4: `post_image_url` Does File I/O Every Call
- **Status**: Deferred (verified)
- **Reason**: `os.path.isfile()` called for each post in multiple places (post.html, related posts, og:image, twitter:image)
- **Files**: `app/__init__.py:204-211`, `app/templates/post.html:8,11,19,65`, `app/templates/_post_content.html`
- **Impact**: Medium - file system calls on every render

### C5: Theme CSS Regenerated Per Request
- **Status**: Deferred (verified)
- **Reason**: `inject_theme` context processor runs on every request, creates new dict with `theme_vars.items()` loop
- **Files**: `app/context_processors.py:137-185`
- **Impact**: Low - settings are cached with 5-min TTL, but template vars created per request

### L5: `backdrop-filter: blur()` GPU Intensive
- **Status**: Deferred (verified)
- **Reason**: Low impact, GPU performance acceptable on modern devices
- **Files**: `app/static/css/style.css:150,151,341,3608`
- **Impact**: Low - used for glassmorphism effects on sidebar/header

### L6: Redundant `tag_counts.get()` Call
- **Status**: Deferred (verified)
- **Reason**: Minimal impact - called twice per tag in sidebar loop
- **Files**: `app/templates/_sidebar.html:14,17`
- **Impact**: Low - dict lookup is O(1)

### L7: `truncate` Called 4x for Same Post
- **Status**: Deferred (verified)
- **Reason**: Minimal impact - Jinja2's truncate is efficient
- **Files**: `app/templates/post.html:4,6,10,18` (meta description, og:description, twitter:description, schema)
- **Impact**: Low - same text truncated 4 times

---

## Known Test Issues

### Media Upload Test
`TestMediaManagement::test_upload_browse_delete_image` occasionally fails due to timing/async issues with image processing. The image upload itself works correctly.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-22 | Verified all deferred items - no completed implementations found |
| 2026-04-21 | Consolidated plan created from plan.md, plan2.md, plan3.md, plan4.md |
| 2026-04-21 | All waves completed (A-I) |
| 2026-04-21 | Plan pruned - completed items removed, deferred items preserved |