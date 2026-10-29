# Project Pages Phase 05 — GitHub-Canonical Release Catalog

> **Plan status: PARTIALLY IMPLEMENTED.** See the completion record below and [project_pages_roadmap.md](project_pages_roadmap.md).

**Date:** 2026-10-28
**Plan ID:** PROJ-05
**Status:** Partially implemented in this worktree
**Prerequisite:** Phase 01; merge after Phase 04 to keep migrations linear.

## Objective

Add optional release/version discovery for a project with a configured **public GitHub repository**. The site's release catalog is a read-only presentation of GitHub release metadata. All initial asset downloads link to GitHub. Neither binary hosting nor GitHub writes are needed.

## Schema and integration

Add `Project.releases_enabled` default false and explicit include/exclude policy for prereleases and drafts (GitHub drafts never exposed). Model:

- `ProjectRelease`: project FK, provider release ID, tag name, display title, release notes Markdown, published/created time, GitHub HTML URL, prerelease flag, source sync timestamp. Unique by project + provider release ID; store tag as data (not a filesystem path).
- `ProjectReleaseAsset`: release FK, provider asset ID, filename, content type, size, canonical browser download URL, optional provider-reported digest, and optional verification status later. Unique by release + provider asset ID.

Use one reversible Alembic migration from the then-current head. Index project and newest-release queries. Avoid treating tags as comparable SemVer without explicitly parsing and validating; use GitHub published time or a documented version sort fallback.

Use the Phase 04 restricted GitHub client if it exists, while keeping docs and releases synchronization independently enabled/configured. Fetch only release metadata and page it with bounded limits. Do not make GitHub calls from visitor requests. Support manual refresh and optional periodic reconciliation with backoff and cache metadata. Distinguish no releases, failed sync, disabled feature, and stale-but-usable cache.

## Rendering and routes

Add `GET /projects/<slug>/releases` and version detail links such as `/projects/<slug>/releases/<tag>` using safely encoded route identifiers. Display release date, latest available published release, prerelease status, release notes rendered by `app/markdown_renderer.py`, asset platform/architecture when metadata can be parsed confidently, asset bytes and direct GitHub download URLs.

Keep GitHub links explicitly recognizable as canonical. Do **not** fabricate checksums when no verified digest exists, infer a CPU architecture from ambiguous filenames as fact, or present an unsigned release as verified.

An optional JSON catalog endpoint may expose normalized DevLog release records, but its schema must be explicit, versioned, and documented. It is not automatically an eggpack or eggup protocol.

## Admin and API

Expose enable/disable, repository identity and manual metadata-refresh controls in project admin, with per-project sync status and errors. Keep actions admin-only and CSRF-protected. Add API scopes for releases read/sync only if needed; protect any manual refresh action from unauthenticated abuse and rate limiting bypass.

GitHub remains canonical: DevLog never edits, creates or deletes GitHub releases. On an upstream deletion, follow a documented reconciliation and stale-data policy; never silently relink an old asset ID to an unrelated binary.

## Tests and acceptance

1. Publish a project without release integration: no releases link, no remote calls and no feature degradation.
2. Enable and import a mocked repository with multiple releases/assets; latest published stable release chosen according to documented policy; include/exclude prerelease settings work; GitHub drafts never appear.
3. External download URL points only to the correct canonical GitHub release asset; malicious or unexpected URL hosts are rejected.
4. Release title/notes are safely rendered, no XSS or markup bypass; assets show honest sizes and digest availability, no assumed cryptographic verification.
5. ETag unchanged, pagination, rate limits, offline GitHub, deleted release, duplicate asset ID and stale-cache behavior are deterministic. No public request hits GitHub.
6. Tests cover upgrade/downgrade, admin authorization/CSRF and no regressions to documentation/local projects or public navbar.
7. Operator docs explain GitHub dependency, caching frequency, and that assets remain hosted on GitHub in this phase.

**Likely files:** `app/models.py` and migration; `app/services/project_releases.py`; `app/routes/public/project_releases.py`; admin sync routes/templates; `app/templates/projects/releases*.html`; docs/OpenAPI if JSON interface is added; tests.

## Phase boundary

No downloading or uploading release assets into the blog, server-side binary proxy, installer manifests, signature verification claims, or alternate download mirrors. Those are Phase 06 and must not delay release catalog availability.

## Completion

**Status:** Partially implemented; acceptance is not complete.

**Implemented:** Reversible `ProjectRelease` / `ProjectReleaseAsset` schema; disabled-by-default public catalog; bounded three-page metadata sync using the restricted GitHub client and ETags; drafts excluded, optional prereleases; only HTTPS `github.com` release and asset URLs retained; sanitized Markdown release notes; admin enable/refresh/status; public cached-only catalog and details; GitHub download links are labeled canonical; provider digests are not described as independently verified. Focused sync/publication and migration tests pass.

**Filter and conditional-request coordination:** the upstream ETag only says that GitHub's release list is unchanged, but the cached catalog also depends on the repository and on whether prereleases are included. `releases_sync_config` stores a fingerprint of that configuration next to the ETag. When the fingerprint no longer matches the current settings the conditional request is dropped and the catalog is fetched in full, so changing the prerelease preference always reconciles the local cache even when upstream did not change at all. Turning the preference back off removes the prerelease rows again.

**Not yet complete:** No periodic reconciliation or explicit stale-but-usable UI; no release API/OpenAPI surface; no admin auth/CSRF regression matrix or rendered XSS browser test; no confidently parsed platform/architecture metadata; manual sync shares repository identity settings with docs. No binaries are mirrored and no installer manifest is emitted.
