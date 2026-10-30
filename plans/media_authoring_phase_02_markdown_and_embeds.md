# Media Authoring Phase 02 — Markdown Video and Safe Embed Blocks

> **Plan status: IMPLEMENTED.** This phase is part of the completed [Media Library and Inline Authoring roadmap](media_authoring_roadmap.md). It depends on MIA-01's validated media URLs and safe download contract.

**Date:** 2026-10-28
**Status:** Implemented
**Phase:** MIA-02
**Prerequisite:** [MIA-01](media_authoring_phase_01_library_and_uploads.md)

## MIA-02A — Controlled inline video markup

Extend the single renderer in `app/markdown_renderer.py` and the shared sanitizer config in `app/markdown_config.py` to preserve the minimal markup required for inline uploaded video (such as `video` and `source`, plus only the required `controls`, `src`, `type`, `preload`, and accessibility attributes). Keep the accepted URL schemes/origins explicit; strip event handlers, styles, script, object/embed and unsupported attributes. Do not trust a filename extension when assigning a `source` MIME type.

Images continue to use standard Markdown image syntax. Add tests that approved `<video>` output survives and malformed/untrusted video markup is stripped, in both the normal renderer and admin preview.

## MIA-02B — Special HTML block grammar

Define a distinct block-level syntax, initially `:::html` … `:::`, for intentionally authored embed markup. Parse it through a controlled Markdown extension or preprocessing stage, then run the complete output through `nh3.clean()` with the shared allowlist. The block marker must not create an unsanitized path or allow raw code blocks to be reinterpreted as HTML.

Permit only the elements and attributes required by documented embed examples. For YouTube, accept only a validated embed URL from approved YouTube hostnames and the expected `/embed/<video-id>` path; reject lookalike hostnames, userinfo, unexpected ports, credentials, `javascript:`, `data:`, and other arbitrary sources. Keep `sandbox`, `allow`, `referrerpolicy`, title, and sizing attributes to a minimal reviewed set. Where possible generate the iframe from a validated provider URL rather than permitting hand-authored arbitrary iframe attributes.

Document the exact syntax and supported embed providers. Initial provider scope: YouTube only; adding providers requires security review, allowlist tests, and CSP updates.

## MIA-02C — CSP, preview, public pages, and feeds

Update `app/__init__.py:set_security_headers()` so enforced and report-only CSP policies agree and `frame-src` contains only explicitly supported embed origins. Add an appropriate `media-src` policy for the actual inline video storage origins (local origin and any configured CDN/public storage origin required by deployment). Do not broaden `default-src` to make media work.

The admin preview, post/page public render, and RSS render all use the same sanitized renderer. Decide whether feeds should emit sanitized embed/video markup or degrade to a safe link/placeholder; implement that policy explicitly without creating a second renderer/sanitizer. Verify both preview HTML and the response CSP.

## MIA-02D — Security regression tests and docs

Replace the existing expectation that every iframe is stripped with tests asserting the intended narrow allowlist: safe approved YouTube embed passes; invalid provider URL and hostile attributes are removed; script/event handlers and dangerous schemes remain blocked. Add HTML-block parsing tests for nesting, malformed/unclosed blocks, fenced code interactions, and multiple embeds. Verify CSP in enforced and debug report-only modes, Markdown preview, post/page render, and RSS policy.

Update the Markdown/sanitizer architecture documentation and agent overrides, including the single renderer contract and provider allowlist owner.

## Expected files

`app/markdown_renderer.py`, `app/markdown_config.py`, `app/markdown_extensions.py` or a dedicated extension, `app/__init__.py`, Markdown and route tests, plus architecture and `AGENTS.override.md` docs. Avoid new dependencies unless a demonstrated parser requirement cannot be met with Python-Markdown and existing `nh3`.

## Acceptance criteria

- [x] Approved local/configured-storage video markup survives; external/unconfigured sources and unsupported attributes are removed.
- [x] `:::html` blocks render safe authored HTML/YouTube embeds through the shared sanitizer; malformed, nested, fenced-code and unclosed block cases remain sanitized.
- [x] Only the exact HTTPS YouTube-nocookie `/embed/<11-character-id>` form can produce an iframe; sandbox/loading/referrer-policy attributes are forced.
- [x] Flask enforced/report-only CSP allow only the supported frame host and necessary media sources; nginx defers CSP to Flask rather than emitting a broader competing policy.
- [x] Admin preview, public rendering and feed rendering share `render_markdown()`; feeds preserve only sanitized approved output.
- [x] Existing Markdown, code blocks, sanitizer and XSS regression tests pass.

## Completion

**Status:** Implemented.

The renderer now accepts controlled uploaded-video markup and the explicit `:::html` block, but sends all output through the existing `nh3` sanitizer. YouTube iframes require a strict hostname/path match and get forced sandbox, lazy-loading and no-referrer attributes. Flask is the sole CSP owner; nginx emits no competing or broader policy. RSS keeps safe embed/video markup through the same renderer; no alternate sanitizer was introduced.

**Verification:** The focused Phase 01/02 regression suite passed (**162 passed**), including preview and feed-extension policy tests. Repository-wide `ruff check .`, `ruff format --check .`, `git diff --check`, and `npm run build` passed. The full suite completed with **4,915 passed, 60 failed, 23 skipped**; none of the failures were in the new media-authoring, Markdown-embed, or media-cleanup test modules. Repository-wide mypy reports 17 existing errors in unrelated files; none are in the changed renderer, sanitizer config, extensions or CSP code.
