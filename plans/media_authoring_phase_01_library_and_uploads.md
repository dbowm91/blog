# Media Authoring Phase 01 — Categorized Library and Uploads

> **Plan status: IMPLEMENTED.** This phase is part of the completed [Media Library and Inline Authoring roadmap](media_authoring_roadmap.md).

**Date:** 2026-10-28
**Status:** Implemented
**Phase:** MIA-01
**Prerequisite:** None

## MIA-01A — Catalog and classification

Extend `app/routes/admin/media.py` and its media-list template so the media manager includes every stored file and supports Images, Videos, and Other categories (including counts/empty states and search/filter behavior). Preserve paging and cache invalidation, but ensure category counts and listings are based on the complete catalog, not a stale image-only subset.

Classification must be based on validated/known content type with safe extension as corroboration. Do not trust filename or browser MIME alone. Treat unknown or conflicting legacy objects as Other and never render them inline. Support S3 metadata/listing and local storage consistently; do not expose filesystem paths or storage secrets.

## MIA-01B — Upload endpoints and validation

Retain compatibility for the existing cover-image and media-library upload flows, or migrate their callers explicitly with regression tests. Add an editor-usable upload endpoint that returns structured JSON and a canonical storage URL, with author/admin authorization, CSRF, request-size enforcement, generated object names, and sanitized errors.

- Images: preserve magic-byte validation, existing size policy and `upload_with_processing()` responsive variants.
- Videos: define the accepted formats and limit; validate actual file content, then store without invoking image processing. Transcoding is out of scope unless separately approved.
- Other files: define arbitrary-file extension/MIME and size behavior; never accept a browser declaration as proof of content. Generated storage names must retain only a validated safe extension needed for download behavior.
- All failure paths must avoid leaving partial objects and must invalidate the media cache only after a successful store.

## MIA-01C — Safe attachment delivery

Provide a stable URL for Markdown attachment links that downloads content rather than rendering it in the site's origin. For local storage, set a safe content type, `Content-Disposition: attachment` with a safely encoded display filename, and `X-Content-Type-Options: nosniff`. For S3-compatible storage, establish equivalent response metadata or proxy through an application route; verify the actual behavior with the configured backend. Do not use a direct public-object URL for arbitrary HTML/SVG/script types unless the storage layer guarantees attachment disposition.

The response must avoid path traversal, arbitrary object-key access, and leaking storage credentials. Determine whether a signed/public URL is necessary for S3 while preserving usable public links.

## MIA-01D — Tests and documentation

Add tests for MIME/signature spoofing, legacy/unknown classifications, upload limits, local/S3 success and failure paths, image-processing isolation, cache invalidation, attachment response headers, safe filenames, authorization and CSRF. Keep browser interactions in `tests/e2e/` if introduced.

Update the media/storage architecture docs with the actual supported types, limits, categorization contract and download behavior. Do not update docs with unverified operational claims.

## Expected files

Likely `app/routes/admin/media.py`, media helpers, storage abstraction, `app/templates/admin/media.html`, media upload JS, tests, and `architecture/infrastructure/storage.md` / `architecture/routes/admin-routes.md`. Exact ownership may change after implementation inspection. No database migration by default.

## Acceptance criteria

- [x] The media manager/catalog classifies stored objects as Images, Videos, and Other, subject to the existing configurable `MEDIA_MAX_FILES` ceiling; S3 inventory reads all continuation pages before applying that cap.
- [x] Image (PNG/JPEG/GIF/WebP), video (signature-checked MP4/WebM), and arbitrary Other upload policies are enforced server-side with `MAX_UPLOAD_SIZE` and a request-body ceiling.
- [x] Images retain existing responsive processing; videos/other files use direct storage and never enter the image pipeline.
- [x] Attachment URLs force `application/octet-stream`, attachment disposition, `nosniff`, and no-store; local, S3 metadata, and application download paths are covered by tests.
- [x] Editor inventory/upload endpoints allow authors/admins; media management/deletion remains admin-only; global CSRF protection applies.
- [x] Existing cover-image upload and media delete/list behavior remain functional.
- [x] Orphan cleanup deletes only signature-verified images that are not referenced by `Post.image` or post/page Markdown; it preserves videos and attachments.
- [x] Focused media/admin/storage/security/author suite, Ruff checks, formatting, and Vite build are run; results are recorded below. Repository-wide mypy retains unrelated existing errors.

## Completion

**Status:** Implemented.

Phase 01 adds category-aware catalog filtering and counts, an author/admin JSON inventory/upload API, signature-validated image/video upload, and arbitrary attachments with forced download delivery. MP4/WebM are served as-is; images alone keep responsive variants. The media library retains its `MEDIA_MAX_FILES` safety cap.

**Verification:** The focused Phase 01/02 regression suite passed (**162 passed**); repository-wide `ruff check .`, `ruff format --check .`, `git diff --check`, and `npm run build` passed. S3 content-type/disposition and paginated listing have mocked unit coverage. The full suite completed with **4,915 passed, 60 failed, 23 skipped**; none of the failures were in the new media-authoring, Markdown-embed, or media-cleanup test modules. Failures were in doctor, deployment integration, filesystem, storage/profile, task, theme, and unrelated integration tests. Repository-wide mypy reports 17 existing errors in `app/config/model.py`, `app/config/secrets.py`, `app/themes/translate.py`, `app/config_legacy.py`, `app/cli.py`, `app/services/operations/database.py`, and `app/services/operations/doctor.py`; no changed media/renderer modules were reported.
