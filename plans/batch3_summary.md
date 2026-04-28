# Plan 10 - Documentation Improvement Plan Summary

## Main Objectives/Tasks

1. **README.md Restructuring** - Transform from feature lists to actionable how-to guides
   - Replace feature list (lines 5-12) with "How to Use" section
   - Add How-to subsections for readers (searching, subscribing, navigating) and admins (creating posts, managing content, configuring newsletter, viewing analytics, managing admins, customizing appearance)
   - Add keyboard shortcuts reference
   - Add REST API section with curl examples
   - Add CLI Commands section with table
   - Expand routes table to include 15+ missing routes
   - Expand configuration to document 14 missing options

2. **AGENTS.md Updates** (minor)
   - Add note at top clarifying file purpose (technical patterns for developers)
   - Add "Features Agents Should Know About" section

3. **Document 32+ undocumented features** with file references and line numbers

## Specific Implementation Details

### README.md New Structure:
- **Quick Start** (keep existing lines 21-38)
- **How to Use DevLog** (new)
  - For Readers: searching, subscribing, navigating
  - For Admins: creating posts, managing content, configuring newsletter, viewing analytics, managing admins, customizing appearance
  - Keyboard Shortcuts
- **Features (With Context)** - feature lists with usage context
- **Configuration** - environment variables + config.toml options
- **REST API** - endpoints table + curl examples
- **CLI Commands** - table with examples
- **Routes** - public + admin tables (30+ routes)
- **Installation** (keep existing lines 19-65)
- **Project Structure** (keep existing lines 162-208)

### Features to Document:
Static Pages, Archive, Search snippets, "Did you mean?", Share Tracking, Short URLs, Preview Links, SEO (OG/Twitter/Schema), Related Posts, Reading Time, Lightbox, TOC, Post Revisions, Bulk Operations, Media Library, Admin Sessions, Multi-Admin, Password Reset, Newsletter Retry, Backup/Restore, Theme Presets, CSS Sanitization, Keyboard Shortcuts, Health Check, Structured Logging, CSP Nonces

### Hardcoded Values Found (Not Configurable):
- Password reset token expiry: 1 hour
- Dashboard cache TTL: 120 seconds
- Media cache TTL: 30 seconds
- Related posts hard limit: 20

## Dependencies/Ordering Requirements

- **Files NOT to modify**: DEPLOY.md (already comprehensive), docs/openapi.yaml (already complete)
- **AGENTS.md** is low priority compared to README.md restructuring
- README.md modifications preserve existing sections (Quick Start lines 21-38, Installation lines 19-65, Project Structure lines 162-208)

## Phase/Wave Organization

The plan is organized into 8 numbered sections:

1. **README.md Restructuring** - Main work (proposed new structure with markdown)
2. **Code References for Documentation** - Feature mapping table with file paths and line numbers
3. **AGENTS.md Updates (Minor)** - Cross-reference additions
4. **Critical Findings from Code** - Hardcoded values, security notes, two-level retry system
5. **Implementation Checklist** - 15+ task items with checkboxes
6. **Documentation Best Practices Applied** - Research findings (Diátaxis Framework, Flask-Blogging, FlaskBlog examples)
7. **Files to Modify** - README.md (High priority), AGENTS.md (Low priority)
8. **Success Criteria** - 8 measurable outcomes

## Success Criteria

After implementation:
- README.md has 0 feature-only lists (all have usage context)
- All 32+ undocumented features documented with file references
- All 20+ configuration options documented with defaults
- Routes table complete (30+ routes for public + admin)
- CLI commands section with examples
- API section with curl examples linking to OpenAPI spec
- How-to sections for: creating posts, configuring newsletter, customizing theme
- AGENTS.md updated with cross-references to README.md
