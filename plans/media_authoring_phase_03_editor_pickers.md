# Media Authoring Phase 03 — Editor Media and Attachment Pickers

> **Plan status: IMPLEMENTED IN WORKTREE (uncommitted).** This phase is part of the active [Media Library and Inline Authoring roadmap](media_authoring_roadmap.md). It depends on MIA-01 categorized media APIs/downloads and MIA-02 safe Markdown rendering. This implementation is not yet released.

**Date:** 2026-10-28
**Status:** Implemented in worktree; validation recorded below
**Phase:** MIA-03
**Prerequisites:** [MIA-01](media_authoring_phase_01_library_and_uploads.md), [MIA-02](media_authoring_phase_02_markdown_and_embeds.md)

## MIA-03A — Separate editor controls

Add two independent, accessible toolbar controls to the shared Markdown editor macro in `app/templates/admin/_editor_body.html`:

1. **Media** icon with a dropdown/picker for inline images and videos. Default to Images/Videos, offer category filtering as useful, and include an inline upload option for supported image/video types.
2. **Attachment** icon with a picker that initially lists Other (non-image/non-video) files and an upload option for the documented arbitrary-file policy. It may offer category changes so an existing image or video can also be chosen as an attachment.

A file selected from the Attachment picker always inserts a Markdown download link, even when the selected item is an image or video. The Media picker inserts `![alt](url)` for an image and the controlled inline-video markup agreed in MIA-02 for a video.

The macro is shared by post and page editors. Keep both controls available anywhere the Markdown body editor is used unless route authorization or a product decision requires a documented distinction. Do not nest forms; use a hidden file input or an independent upload request.

## MIA-03B — Upload, insert, and editor-state integration

Reuse the authenticated editor-facing JSON APIs from MIA-01 and the shared CSRF helper. Keep the editor's insertion position stable while the user opens the picker or chooses a file. After upload, insert the returned canonical URL and safe display name only after server success. An upload error must preserve the body text and restore control state.

Insertions must use the existing textarea selection/replacement semantics and dispatch a bubbling input event, plus the editor's structural history event where appropriate, so live preview, autosave, dirty detection, counters and undo/redo see the change. Never insert raw unsanitized server metadata into HTML or assume browser MIME/filename are safe. Preserve focus and keyboard navigation; provide labels, status/error announcements, and mobile-usable picker behavior.

## MIA-03C — Picker inventory and acceptance tests

Picker inventory, category tabs/search, upload status, and the media manager must share the same server-side catalog semantics. Avoid maintaining a second browser-only list or classifier. The attachment picker should initially filter to Other but include previously uploaded images/videos when the user changes category.

Add JS/module tests for range insertion, image/video/attachment syntax, upload success/failure, cursor restoration, input/history events, repeated clicks and cancellation. Add Flask tests for picker data and auth/CSRF. Add browser E2E coverage on the dedicated E2E database for upload/select/insert/preview and normal post/page save. Verify click does not submit the editor form, and ensure the attachment URL downloads content as specified in MIA-01.

## MIA-03D — Documentation and build checks

Update editor/media operator guidance, architecture docs for admin routes, storage and frontend integration, plus relevant module override contracts. State accepted file types/limits and the difference between inline Media and Attachment selection. Run focused backend/security tests, E2E, `ruff check .`, `ruff format --check .`, `mypy app/ devlog_cli/`, `npm run build`, dependency-manifest consistency, and the relevant full/release suite as available; record actual results.

## Expected files

`app/templates/admin/_editor_body.html`, `app/static/js/admin/markdown-toolbar.js` or a small imported editor module, `app/static/js/admin/editor.js`, CSS as needed, route/API tests, `tests/e2e/`, and architecture/operator docs. Avoid changing route-to-module mapping if the new module is statically imported by the existing editor module.

## Acceptance criteria

- [x] Media and Attachment have distinct, understandable icons, labels, picker states, and insertion semantics.
- [x] Media picker supports image/video selection and inline upload; Attachment picker defaults to Other and supports arbitrary-file upload per MIA-01 policy.
- [x] Selecting any category through Attachment inserts a Markdown download link; Media selection inserts inline image/video markup.
- [x] Insertions preserve selection/focus and integrate with preview, autosave, dirty state, counters, and history.
- [x] Upload and picker operations use the author-protected catalog/upload APIs, shared CSRF helper, server validation, configured size limits, safe URLs, and accessible status/focus behavior.
- [x] Post and page editors share the same controls; Chromium E2E covers mobile layout, keyboard Escape/focus restoration, and light-scheme rendering.
- [x] Automated checks and browser E2E results are recorded accurately below, including known unrelated mypy errors.

## Completion

**Status:** Implemented in worktree; uncommitted and unreleased.

The shared editor now exposes separate Media and Attachment dialogs on post and page forms. Both consume the author-protected categorized catalog, use the CSRF helper for uploads, and insert only canonical URLs after successful server responses. Media inserts Markdown images or controlled video markup using the catalog's allowlisted server `mime_type`; Attachment inserts a forced-download Markdown link for every selectable category. Upload failure leaves the draft unchanged. Picker selection dispatches the editor input/history events and restores focus; the picker has responsive and screen-reader status treatment.

**Validation run:**

- `ADMIN_PASSWORD=… SECRET_KEY=… .venv/bin/python -m pytest tests/test_media_authoring.py tests/test_admin_contracts.py tests/test_author_role.py -q` — 69 passed.
- `ADMIN_PASSWORD=… SECRET_KEY=… .venv/bin/python -m pytest tests/e2e/test_media_picker.py -q` — 2 passed in Chromium; covers post/page selection, inline image/video, download-link attachments, upload failure/success, CSRF header, preview/history, mobile viewport, light scheme, Escape/focus restoration, and normal post/page form saves.
- `ruff check .`, `ruff format --check .`, `git diff --check` — passed.
- `npm run build` — passed.
- `.venv/bin/python scripts/check_dependency_manifest_consistency.py` — passed.
- `mypy app/ devlog_cli/` — not clean: 17 pre-existing errors in seven unrelated modules (`app/config/model.py`, `app/config/secrets.py`, `app/themes/translate.py`, `app/config_legacy.py`, `app/cli.py`, `app/services/operations/database.py`, and `app/services/operations/doctor.py`).
- Full repository/release suite was not rerun for this phase; the prior Phase 01/02 full-suite baseline remains recorded separately.
