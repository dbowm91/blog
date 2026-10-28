# Project Pages Phase 04 — GitHub Documentation Snapshots

> **Plan status: PARTIALLY IMPLEMENTED.** See [project_pages_roadmap.md](project_pages_roadmap.md).

**Date:** 2026-10-28
**Plan ID:** PROJ-04
**Status:** Partially implemented in this worktree
**Prerequisite:** Phase 03 merged.

## Objective

Allow a project's documentation to originate in a configured **public** GitHub repository path, while still rendering locally cached, verified Markdown via Phase 03's viewer. Repo content is an upstream source, not a request-time dependency or remote-rendered HTML. Locally authored docs remain supported and must not be overwritten inadvertently.

## Source contract and schema

Store explicit source configuration per project (or project-doc-source record): `source_kind=local|github`, validated `owner/repo`, docs root path (usually `docs/`), ref selector (branch/tag; default configured branch), update policy (manual default, bounded periodic opt-in), and optional documented entrypoint. Do not accept arbitrary URL bases or GitHub API URLs as configuration.

Introduce immutable `ProjectDocsSnapshot` metadata: project/source, source ref, resolved commit SHA, acquisition timestamp, status, file count, total size, content digest or manifest digest, and error summary. A staging/import batch must be distinguishable from the last published snapshot. Remote document rows must reference the activated snapshot or stable version identity; don't merge them into mutable local-authored rows without provenance.

Define configurable limits: maximum files, Markdown bytes per file and total, image count/size, tree depth, sync frequency, and request budget. Keep defaults suitable for low-memory/SBC installs. No private repository token requirement in the initial implementation.

## Sync transaction

Build a GitHub client in a service, not template/routes. Validate repository identity against strict GitHub owner/name grammar; construct API requests from typed components and a fixed GitHub host, not user-provided fetch URLs. Use bounded connect/read timeouts, rate-limit-aware retry/backoff, ETags/conditional requests, explicit no-redirect or strictly same-host redirects, and response content-type/size verification.

Resolve branch/tag to a specific commit SHA, enumerate supported Markdown files under the approved docs prefix and fetch exact file revisions. Exclude symlinks, submodule entries, Git LFS pointers unless supported explicitly, non-Markdown text, oversized resources and path aliases. Normalize every Markdown path using the Phase 03 resolver before staging.

Validate and prepare the complete prospective snapshot before atomic activation. Only publish a new snapshot after all required documents and references are safe and complete; on any failure retain the previous successful snapshot and expose a **sync failure status to the admin**, not a broken public docs site. Ensure concurrent manual and scheduled syncs cannot interleave activation; apply DB locking/lease discipline across workers.

Expose manual `Sync docs` and inspect-status actions to admins. Optional periodic reconciliation may use the existing scheduler only when enabled on a single application instance (the documented APScheduler limitation). Do not introduce Celery or Redis as a mandatory dependency. Public page views must perform zero GitHub network calls.

## Relative links, images and CSP

Use the same sanitized Markdown renderer and docs link resolver, but give it a snapshot manifest to map local relative paths and fragments. Restrict cross-file links to paths in the imported manifest; external links remain normal HTTPS links. Imported images must either be explicitly supported via bounded, verified local proxy/cache or left as safe external links consistent with CSP. Prefer same-origin stored images in a project-specific assets namespace, never global arbitrary `/static/uploads` path concatenation. Validate extensions, MIME signatures, size, hash, and storage keys. Imported SVG should be rejected or sanitized by existing trusted SVG machinery; never display raw remote HTML.

`app/__init__.py` currently sets `img-src 'self' data:` plus configured CDN; do not silently broaden it to all GitHub/raw hosts. Local image cache plus same-origin URLs is the preferred compatible approach.

## Tests and acceptance

1. Import a sample repository with root README, nested docs and relative links using mocked GitHub; no external network required in CI. Verify all displayed documents are tied to one resolved commit.
2. A sync failure mid-tree, ETag unchanged, rate limit, transient 5xx, malformed Markdown file, network timeout or malicious path leaves the last good snapshot publicly intact and records a bounded admin status.
3. Two concurrent sync triggers do not publish mixed refs or duplicate documents. Repeated sync of unchanged commit is idempotent and cheap.
4. SSRF probes, arbitrary hosts, encoded traversal, symlinks, submodules, private repo failures, redirects and oversized blobs are rejected or safely skipped per documented policy.
5. Docs relative links/images preserve project scope; anchors, TOC, highlighting and nav work on the server-rendered snapshot and obey CSP; no raw GitHub HTML is embedded.
6. Deleting/unpublishing the project removes public routes and links, without removing unrelated local media or documents. Storage cleanup has a safe, bounded orphan policy.
7. Tests verify zero outbound repository requests per public GET and graceful operation when GitHub is offline or the feature is not configured.

**Likely files:** `app/services/github_client.py`, `app/services/project_docs_sync.py`, project-doc models/migration, new admin sync endpoints/status templates, a bounded image asset service, scheduler registration (optional), tests with HTTP fixtures, and operator documentation.

## Phase boundary

Do not fetch release binaries, attempt repository writes, build artifacts, ingest arbitrary private repositories or implement a general GitHub mirror. Phase 05 owns releases; Phase 06 owns artifact bytes.

## Completion

**Status:** Partially implemented; acceptance is not complete.

**Implemented:** Fixed-host bounded GitHub API client with ETags, retry/rate-limit metadata and redirect rejection; owner/repository validation; manual public-repository sync of a bounded commit-pinned Markdown tree; path/body/count/aggregate limits; immutable snapshot rows with commit SHA and manifest digest; snapshot-bound docs; atomic active pointer update; local docs retained; failure state leaves previous active snapshot unchanged; admin sync/status; public reads use cached DB content only. Mocked GitHub sync and migration tests pass.

**Not yet complete:** No cross-process DB lease/lock, scheduled opt-in reconciliation, GitHub image import/cache, tree-depth/request-budget configurable settings, or concurrency/rate-limit/mid-stream failure matrix. GitHub docs images are not automatically copied; they need a project-scoped uploaded asset. These gaps must be addressed before calling Phase 04 complete.
