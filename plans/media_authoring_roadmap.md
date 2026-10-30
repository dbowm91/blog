# Media Library and Inline Authoring — Roadmap

> **Plan status: COMPLETE IN WORKTREE (uncommitted).** Phases 01–03 are implemented and have phase-specific validation records; this work has not been released.

**Date:** 2026-10-28
**Status:** Phases 01–03 implemented in the worktree; uncommitted and unreleased
**Series prefix:** MIA
**Origin:** operator request to manage images, videos, and other files in one media library; insert inline media and downloadable attachments from the editor; and support safe embedded HTML blocks.

## Goal

Extend DevLog's current image-only media library into a categorized library for **images**, **videos**, and **other files**. Add two separate editor controls:

- **Media**: a dropdown/picker scoped initially to images and videos, with upload available in the picker; selecting an image inserts Markdown image syntax and selecting a video inserts supported inline-video markup.
- **Attachment**: a picker scoped initially to other (non-image/non-video) files, with arbitrary-file upload; selecting any file—including an image or video—adds a Markdown download link rather than inline rendering.

Also add a special Markdown block syntax for authored HTML embeds, including third-party video embeds such as YouTube. Preserve the single server-side Markdown renderer and make every accepted tag, attribute, URL, and embed host explicit and sanitized. This is not a request to allow unrestricted executable HTML.

## Verified integration points and constraints

- `app/routes/admin/media.py` owns the authenticated media library and its current redirect-based, image-only upload route. It uses `_get_cached_media_list()` and explicitly invalidates its cache after upload/delete.
- `app/routes/admin/helpers/images.py:_save_image()` validates image signatures, applies the configured maximum upload size, stores images and queues responsive-image processing through `app/storage.py:upload_with_processing()`.
- `app/storage.py` provides local and S3-compatible storage with `save`, `load`, `delete`, `exists`, `url`, and listing operations. Image variant generation is image-specific and must not be run on videos or arbitrary files.
- `app/templates/admin/media.html` and `app/static/js/upload.js` currently implement an image-only media gallery/upload flow. `app/static/js/main.js` routes editor and media-library modules.
- `app/templates/admin/_editor_body.html` supplies the shared Markdown editor to post and page editing. `app/static/js/admin/markdown-toolbar.js` owns Markdown toolbar interactions; `app/static/js/admin/editor.js` owns preview, autosave, dirty state, and editor history integration.
- `app/markdown_renderer.py` is the sole Markdown producer. `app/markdown_config.py` is the shared `nh3.clean()` allowlist. The same renderer is used by public templates, the admin preview, and RSS feeds.
- The current allowlist permits `img` but not `video`, `source`, or `iframe`; the CSP in `app/__init__.py:set_security_headers()` sets `frame-src 'none'` and has no explicit `media-src`.
- CSRF is globally required for browser POST requests. Existing browser-level tests belong under `tests/e2e/` on the dedicated E2E database.

## Phases — execute in order

| Phase | File | Deliverable | Status |
|---|---|---|---|
| 01 | [`media_authoring_phase_01_library_and_uploads.md`](media_authoring_phase_01_library_and_uploads.md) | Categorized inventory, type-specific validation/storage, author/admin media APIs, safe downloads | Implemented |
| 02 | [`media_authoring_phase_02_markdown_and_embeds.md`](media_authoring_phase_02_markdown_and_embeds.md) | Sanitized inline video and explicit HTML/embed block rendering with CSP and feed behavior | Implemented |
| 03 | [`media_authoring_phase_03_editor_pickers.md`](media_authoring_phase_03_editor_pickers.md) | Separate Media and Attachment toolbar pickers, inline upload, correct Markdown insertion | Implemented in worktree |

## Architecture and security contracts

`authenticated editor → categorized media API → validated type-specific storage → picker selection → Markdown source → single sanitized renderer → preview/public page/feed policy`.

- **One media catalogue.** Classify each stored object as image, video, or other using signature checks plus a supported extension—not filename extension alone. The media manager/catalog respects the existing configurable `MEDIA_MAX_FILES` ceiling (1000 by default), displays the three category counts, and does not expose filesystem paths or storage credentials.
- **Separate upload flows, shared storage.** Keep image decoding/variant processing image-only. Videos and other files require explicit content/size validation, generated storage names, upload limits, and failure cleanup. Do not trust the browser-provided MIME type.
- **Arbitrary uploads are downloads, not inline content.** Files eligible for the Attachment picker (validated images/videos or generated `.attachment` keys) produce `[filename](download-url)` syntax, regardless of media category. `/media/download/<key>` serves `application/octet-stream`, attachment disposition, `nosniff`, and no-store. Local `.attachment` objects and S3 objects also have forced-download behavior. Legacy Other objects without generated attachment keys are visible for management but are not eligible for public download.
- **Inline media remains narrow.** Images use standard Markdown image syntax. Videos use a controlled `<video controls>` / `<source>` representation with only required safe attributes and permitted local/storage URL schemes. Never permit event-handler attributes or arbitrary CSS.
- **HTML blocks are not a sanitizer bypass.** Define a visibly distinct block syntax (for example, `:::html` … `:::`) and process its contents through the same final sanitizer as all Markdown output. Permit only the required presentation/embed tags and attributes. For third-party iframes, parse and validate the URL against an explicit provider host/path allowlist; do not accept arbitrary iframe `src` values. Expand `frame-src` only to approved providers. Any provider allowlist change must update tests and CSP together.
- **One renderer everywhere.** Admin preview and published post/page rendering use the same sanitized renderer; RSS retains that same safe output. There is no unsanitized alternate feed path.
- **No schema migration unless evidence requires one.** Existing files are storage objects; categorization should be derived from validated metadata/bytes unless the implementation demonstrates that a persistent media record is necessary. Avoid adding a second source of truth for files.

## Acceptance criteria

- The admin media manager can display and filter all stored files as images, videos, or other; image cards retain image previews, video cards have suitable video treatment, and other cards show safe file metadata.
- Editor pickers use the same categorized media source and show loading, empty, error, and upload states accessibly.
- Media picker uploads accept supported image/video types only and insert inline rendering markup; image upload retains existing responsive processing and video never enters that pipeline.
- Attachment picker accepts the documented arbitrary-file policy and inserts a download link for any selected file. Clicking that link downloads rather than executing uploaded content in the site origin.
- Markdown HTML block supports documented safe use cases and rejects executable tags, event handlers, dangerous URL schemes, and unapproved iframe hosts in both preview and rendered content.
- CSRF, authentication/author authorization, size limits, and server-side validation apply to every upload/list/download management endpoint as appropriate.
- Local and S3 storage paths are covered. Existing image cover uploads, media library behavior, Markdown preview, and post/page editing continue to work.
- Tests cover categorization, spoofed types, upload limits, storage errors, cache invalidation, download headers, inline insertion, escaping, sanitizer/CSP policy, and RSS policy. Browser coverage runs under `tests/e2e/`.
- Relevant architecture docs and module overrides describe the shipped contracts after implementation. Each completed phase records actual checks in its own `## Completion` section; do not mark unrun checks as passed.

## Progress

Phases 01–03 are implemented in this worktree, with phase-specific completion and validation records in their plan files. The shared editor now has distinct toolbar controls and picker flows for inline media and forced-download attachments. The implementation remains uncommitted and unreleased.

## Resolved implementation choices

1. Videos are accepted as MP4 or WebM with matching container signature and stored as-is; no transcoding is performed. The existing `MAX_UPLOAD_SIZE` applies (10 MiB by default).
2. Other files receive generated `.attachment` object keys and download via `/media/download/<key>` with octet-stream content type, attachment disposition, `nosniff`, and no-store. S3 writes also set attachment metadata; local static responses for `.attachment` objects force download.
3. Legacy objects classify as inline only when extension and signature agree for supported image/video types. Unknown or conflicting files are Other; only validated media and generated `.attachment` keys receive safe download URLs. Legacy Other objects without generated attachment keys remain visible for management but are not publicly downloadable.
4. The opt-in syntax is `:::html` … `:::`. Iframes are restricted to `https://www.youtube-nocookie.com/embed/<11-character-id>` with no query, fragment, userinfo, or custom port; CSP and sanitizer remain aligned. No additional providers are supported.
5. RSS uses the same renderer and therefore emits the same sanitized, approved video/embed markup. There is no alternate sanitizer.
6. Existing `MEDIA_MAX_FILES` bounds the catalog to its configured maximum (1000 by default); the manager indicates when it reaches the ceiling. S3 listing follows continuation tokens before applying that configured cap.

## Out of scope

No public unauthenticated upload API, file editing/conversion UI, general-purpose browser HTML execution, arbitrary third-party iframe origins, automatic video transcoding, media database/catalog migration without a demonstrated need, or public file privacy controls beyond safe download delivery.
