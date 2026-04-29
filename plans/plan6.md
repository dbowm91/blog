# Documentation Improvement Plan v2

**Last Updated**: 2026-04-28  
**Status**: Ready for Review  
**Estimated Implementation Time**: 6-8 hours

## TL;DR (Executive Summary)

This plan transforms DevLog's documentation from **feature-listing style** to **task-oriented documentation** using 2025-2026 best practices (Docsio, Mintlify, Textpattern CMS). 

**Key Changes**:
- Rewrite README.md (302 → 550 lines) with task-oriented content
- Create USAGE.md (new, 400-500 lines) with step-by-step guides
- Improve DEPLOY.md with ToC, Quick Deploy, Troubleshooting
- Add missing features to AGENTS.md (15 features currently missing)
- Enhance docs/openapi.yaml with request/response examples
- Fix 3 identified bugs alongside documentation (HN platform mismatch, JSON Feed spec compliance, timing attack)

**Success Criteria**: Users can accomplish tasks without reading source code; no feature is just "listed" without a "How to" example.

## Goal

Transform the DevLog blog documentation from **feature-listing style** to **task-oriented, high-value documentation** that helps users accomplish real tasks quickly and confidently.

## Scope

- **README.md** — Primary user-facing documentation (rewrite)
- **USAGE.md** — Create detailed user guide (new file)
- **DEPLOY.md** — Improve structure and add troubleshooting (modify)
- **AGENTS.md** — Add missing feature documentation (modify)
- **docs/openapi.yaml** — Add examples to API endpoints (modify)

Out of scope: ARCHITECTURE.md (optional, low priority)

---

## Part 1: Current State Audit

### Features in Code but MISSING from README.md

| # | Feature | Code Location | Impact |
|---|---------|---------------|--------|
| 1 | **JSON Feed** (`/json`) | `app/routes/rss.py:103-151` | Users don't know JSON Feed exists |
| 2 | **Static Pages** | `app/models.py:72-94`, `app/routes/admin/pages.py` | No documentation on creating About/Contact pages |
| 3 | **Short URLs** (`/s/<code>`) | `app/base62.py`, `app/models.py:143-144` | Sharing feature undocumented |
| 4 | **Preview Links** (draft sharing) | `app/routes/admin/posts.py:447-469` | No docs on sharing drafts securely |
| 5 | **Scheduled Publishing** | `app/scheduler.py:222-285` | Users don't know posts can be scheduled |
| 6 | **Post Revisions** | `app/models.py:150-168` | Restore functionality undocumented |
| 7 | **Archive Page** | `app/routes/public.py:120-219` | No mention of archive browsing |
| 8 | **Related Posts** | `app/routes/public.py:73-94` | Automatic related posts feature hidden |
| 9 | **Share Tracking** | `app/models.py:216-231` | Analytics feature not explained |
| 10 | **Health Check** (`/health`) | `app/routes/public.py:828-914` | Monitoring endpoint undocumented |
| 11 | **Multi-Admin** | `app/routes/admin/users.py` | Brief mention only, no workflow |
| 12 | **Session Management** | `app/routes/admin/sessions.py` | Missing from docs entirely |
| 13 | **Media Library** | `app/routes/admin/media.py` | Listed but no usage details |
| 14 | **Analytics Dashboard** | `app/routes/admin/analytics.py` | Not in features list |
| 15 | **Password Reset Flow** | `app/routes/admin/auth.py:123-223` | Listed but no flow explanation |

### Features That Are Just "Listed" Without Value

| Feature | Current Text | Problem |
|---------|-------------|----------|
| Blog posts | "Markdown editor with image uploads" | No explanation of *how* to upload, supported formats, magic byte validation |
| Admin dashboard | "Admin dashboard" | Vague — doesn't explain *what* you can do there |
| Newsletter | "Email subscriptions with confirmation" | Doesn't explain SMTP config, scheduling, testing |
| Search | "Full-text search across posts" | Doesn't mention FTS5 vs LIKE fallback, prefix matching |
| Security | "CSRF protection, security headers" | Doesn't explain *what* is protected or *how* it works |

### Identified Code Bugs (Fix Alongside Documentation)

| Bug | Location | Impact |
|-----|----------|--------|
| HN platform mismatch | `app/templates/_share_buttons.html` uses `data-platform="hn"`, but `app/routes/api.py:125` expects `"hackernews"` | Hacker News shares not tracked |
| JSON Feed missing `content_html` | `app/routes/rss.py:138` only provides `content_text` | Non-compliant with JSON Feed 1.1 spec |
| Preview link token comparison | `app/routes/public.py:790-791` uses `!=` instead of `not hmac.compare_digest()` | Timing attack vulnerability (minor) |

---

## Part 2: Documentation Best Practices (2025-2026)

Research sources: Docsio (2026), Mintlify (2026), Textpattern CMS, River (2025)

### Core Principles

1. **Task-Oriented > Feature-Lists**
   - ❌ "Blog posts — Markdown editor"
   - ✅ "Writing Posts: Create, edit, and publish with Markdown"

2. **Progressive Disclosure**
   - Beginner: Quick Start (get productive in 5 minutes)
   - Intermediate: Core features (3-5 most common tasks)
   - Advanced: Configuration, API, CLI

3. **Embed Examples Everywhere**
   - Code blocks for configuration
   - Step-by-step workflows for UI tasks
   - Example requests/responses for API

4. **Troubleshooting from Real Issues**
   - Document the 10-15 most common problems
   - Include "Cause" and "Solution" columns
   - Update FAQ monthly from support tickets

5. **Never Assume Knowledge**
   - Explain what FTS5 is when mentioning search
   - Explain what base62 encoding is when mentioning short URLs
   - Define acronyms on first use

---

## Part 3: Proposed Changes

### A. README.md Rewrite (High Priority)

**Current**: 302 lines, feature listings  
**Target**: 450-550 lines, task-oriented with examples  
**Estimated Time**: 2-3 hours

**Note**: The markdown block below is the **proposed new README.md content**. It replaces the entire current file.

#### Proposed README.md Content

```markdown
# DevLog

[1 paragraph: What it is, who it's for, key differentiator]

## Quick Start
...
```

---

## Part 4: Implementation Checklist

### Phase 1: README.md Rewrite (High Priority)
- [ ] Replace current content with new task-oriented structure above
- [ ] Add all 15 missing features with full explanations
- [ ] Add "Quick Start" section with first post walkthrough
- [ ] Add "Configuration Reference" with all config.toml options
- [ ] Add "Troubleshooting" section with 15 common issues
- [ ] Add "FAQ" section with 10 common questions
- [ ] Update badge/shield links if needed

### Phase 2: Create USAGE.md (High Priority)
Create `/home/sugarwookie/projects/blog/USAGE.md` (400-500 lines):

- [ ] **Getting Started** (50 lines)
  - First post, first subscriber, basic config.toml setup
  - First admin user creation
  
- [ ] **Writing Posts** (100 lines)
  - Markdown guide with examples
  - Image uploads (supported formats, size limits)
  - Tags and categories
  - Scheduling and revisions
  - Preview links and short URLs
  
- [ ] **Customizing Appearance** (75 lines)
  - Theme presets explanation
  - Custom CSS variables reference
  - Logo and favicon changes
  
- [ ] **Newsletter Management** (75 lines)
  - SMTP configuration step-by-step
  - Subscriber management UI
  - Scheduler settings and testing
  
- [ ] **Admin Tasks** (100 lines)
  - User management (create, promote, demote, transfer owner)
  - Session management
  - Media library usage
  - Backup/restore procedures
  - Analytics interpretation
  
- [ ] **API Usage** (50 lines)
  - Setting API_KEY
  - Authentication examples
  - Common operations with curl examples

### Phase 3: DEPLOY.md Improvements (Medium Priority)
- [ ] Add table of contents at top (with anchor links)
- [ ] Add "Quick Deploy" section at top (simple single-server deployment)
- [ ] Add "Troubleshooting" section (common deployment issues)
- [ ] Add "Performance Tuning" section (workers, timeouts, caching)
- [ ] Cross-reference README.md for feature explanations
- [ ] Add nginx rate limiting examples (mentioned in AGENTS.md)

### Phase 4: docs/openapi.yaml (Medium Priority)
- [ ] Add request/response examples to each endpoint
- [ ] Document authentication error responses (401, 503)
- [ ] Add examples for common operations (create post, list subscribers)
- [ ] Fix JSON Feed reference (currently says "RSS Feed" incorrectly)

### Phase 5: AGENTS.md Updates (High Priority)
- [ ] Add JSON Feed documentation (currently missing)
- [ ] Add Preview Links documentation
- [ ] Add Scheduled Publishing details
- [ ] Add Post Revisions workflow
- [ ] Add Health Check endpoint documentation
- [ ] Add Share Tracking explanation
- [ ] Fix any outdated information

### Phase 6: Fix Identified Bugs (Medium Priority)
- [ ] Fix HN platform mismatch (`hn` → `hackernews` in template)
- [ ] Add `content_html` to JSON Feed response
- [ ] Fix preview link token comparison (use `hmac.compare_digest()`)

---

## Part 5: Success Metrics

Documentation will be considered successful when:

1. ✅ **Users can accomplish tasks without reading source code**
   - Write a post, customize themes, manage subscribers - all documented step-by-step

2. ✅ **No feature is just "listed"**
   - Every feature has at least one "How to" example or workflow

3. ✅ **Common issues are documented**
   - Troubleshooting covers 15 most common problems
   - FAQ has 10 common questions (update monthly)

4. ✅ **Developers understand patterns**
   - AGENTS.md/ARCHITECTURE.md covers all key patterns and gotchas

5. ✅ **API users have examples**
   - OpenAPI spec includes request/response samples for all endpoints

---

## Appendix: File Paths Reference

### Documentation Files to Create/Modify

| File | Action | Priority | Est. Lines |
|------|--------|----------|------------|
| `/home/sugarwookie/projects/blog/README.md` | Rewrite | High | 450-550 |
| `/home/sugarwookie/projects/blog/USAGE.md` | Create | High | 400-500 |
| `/home/sugarwookie/projects/blog/DEPLOY.md` | Improve | Medium | +100 |
| `/home/sugarwookie/projects/blog/docs/openapi.yaml` | Enhance | Medium | +200 |
| `/home/sugarwookie/projects/blog/AGENTS.md` | Update | High | +150 |
| `/home/sugarwookie/projects/blog/ARCHITECTURE.md` | Create (optional) | Low | 300 |

### Key Source Files Referenced

| File | Purpose |
|------|---------|
| `/home/sugarwookie/projects/blog/app/models.py` | All database models |
| `/home/sugarwookie/projects/blog/app/routes/public.py` | Public routes (posts, pages, search, archive, health) |
| `/home/sugarwookie/projects/blog/app/routes/admin/posts.py` | Post CRUD, revisions, preview |
| `/home/sugarwookie/projects/blog/app/routes/admin/users.py` | User management, promote/demote |
| `/home/sugarwookie/projects/blog/app/routes/admin/backup.py` | Backup/restore/verify |
| `/home/sugarwookie/projects/blog/app/scheduler.py` | Newsletter, scheduled posts |
| `/home/sugarwookie/projects/blog/app/config.py` | All configuration loading |
| `/home/sugarwookie/projects/blog/app/cli.py` | CLI commands |
| `/home/sugarwookie/projects/blog/docs/openapi.yaml` | API documentation |

### Identified Bugs to Fix

| Bug | File | Fix |
|-----|------|-----|
| HN platform mismatch | `app/templates/_share_buttons.html` | Change `data-platform="hn"` to `data-platform="hackernews"` |
| JSON Feed missing `content_html` | `app/routes/rss.py:138` | Add `content_html` field to JSON response |
| Preview token timing | `app/routes/public.py:790-791` | Use `not hmac.compare_digest()` instead of `!=` |
