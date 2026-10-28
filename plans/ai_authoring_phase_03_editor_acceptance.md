# AI Authoring Phase 03 — Editor UX, Draft Semantics, and Acceptance

> **Plan status: IMPLEMENTED — provider-use approval and live smoke gate remain open.** Requires [AIA-01](ai_authoring_phase_01_provider_summary.md) and [AIA-02](ai_authoring_phase_02_tag_reconciliation.md). Behavior is documented in `architecture/frontend/overview.md`.

**Date:** 2026-10-28
**Status:** Implemented; provider-use authorization gate remains open
**Phase:** AIA-03

## AIA-03A — Conditional Jinja controls

In `app/routes/admin/posts/editor.py:_render_editor()` compute a trusted `ai_assist_available` flag; show buttons only when configured, on **post** new/edit, and nowhere public or on the generic page editor. In `app/templates/admin/editor.html` place `type="button"` actions beside the existing Summary and Tags labels: **AI write TL;DR** and **AI suggest tags**. Use `url_for()` for endpoint URL exposed through a data attribute; never render model credentials or arbitrary provider URLs. Leave existing field IDs and form/publish behavior intact.

Add a concise disclosure that pressing a button sends the current unsaved article to the configured remote AI service. No automatic sending during page load, focus, preview or save.

Field-local loading/error/suggestion/status regions should use accessible labels and `aria-live`; model output is **plain text** inserted with `textContent` or form values, never `innerHTML`. Reuse existing theme tokens and existing admin/form CSS; add minimal styles to `app/static/css/admin.css` only if necessary.

## AIA-03B — Fetch, review, apply

Extend `app/static/js/admin/editor.js`, optionally importing a small `admin/ai-assist.js` from it. No additional route mapping is necessary if statically imported. Read current title/body from the DOM at click time, send `fetch` JSON to the URL provided by the server with `csrfHeaders()` from `app/static/js/shared/utils.js`. Prevent concurrent same-form requests, disable controls during active inference, restore on completion, and handle network errors, auth expiry, 413, 429, 503 and malformed JSON. No automatic retries.

Snapshot title/body and the destination field at request start. If the user edits source or destination while inference runs, never overwrite those newer edits. Show the suggestion for explicit review/acceptance or offer to regenerate. Cancellation or error must preserve all fields and not submit the form.

Summary: show proposed plain-text TL;DR, then explicit **Apply/Replace**. Tags: show proposed canonical tags (optionally identify reused/new), then **Apply suggestions** by merging with already typed tags with deduplication; never delete manually entered tags by default. An optional Replace mode requires separate explicit approval. Only normal form Save/Create persists.

On Apply update the existing form input `value` and dispatch bubbling `input` and `change` so existing autosave, dirty-state and other listeners observe it; maintain sensible keyboard/focus behavior. Respect author-entered text and leave no hidden AI-only persistence state.

## AIA-03C — Close existing draft/tag inconsistency

Current `editor.js` autosave/restore and `checkDirty()` omit tags. Include tags alongside title/body/summary in local draft data, trigger save/dirty checks on tags input changes, and restore them within the existing user-approved draft recovery flow. Keep current restrictions for restoring drafts with nonempty persisted content unless deliberately addressed and tested; do not silently broaden it. Ensure generated edits and manual edits take the same path. Dispatch events needed for summary and tags; ensure unsaved warning, word/preview counters and edit history do not regress.

Do not store provider keys, prompts, tag catalogs, model responses or any remote history in localStorage. Existing local author drafts remain a separate, preexisting feature.

## AIA-03D — Integrated tests

Use `tests/test_ai_assist.py` for conditional template/route checks and new `tests/e2e/test_ai_assist.py` for browser behavior with stubbed inference, never a real provider in CI. E2E must use its own database, not the session-scoped migration test DB; see `tests/AGENTS.override.md`. Cover:

- No key: missing buttons on new/edit and normal previews/saves/tags still work.
- Key: buttons appear only on authorized post editors, not page editors/public pages.
- Click does not submit; request uses current unsaved title/body and correct CSRF header, never credential.
- Summary proposal accepted/cancelled, existing summary not silently overwritten, stale responses safe.
- Tags merge into manually entered values, deduplicate, maintain authoritative canonical names; nothing persisted before Save.
- Both manual/generated tags trigger autosave, draft restoration and unsaved-changes warning.
- Loading, async errors, focus, keyboard, screen-reader updates, mobile and both color schemes are usable.
- Two-pass failures never corrupt draft data.

## AIA-03E — Documentation and release gates

Update `architecture/routes/admin-routes.md`, `architecture/services/overview.md`, `architecture/services/tag.md`, `architecture/frontend/overview.md`, relevant `AGENTS.override.md` cross-layer rules, `USAGE.md` and sample config/env docs. Explain key removal as disable control, external data transfer, limitations and provider-policy requirement.

Run targeted pytest/config/security/route tests, `ruff check .`, `ruff format --check .`, `mypy app/ devlog_cli/`, `npm run build`, dependency manifest check and full suite/E2E as available. CI tests are fully stubbed. A real Go request is permitted only **after** external use for non-coding blog authoring has been confirmed acceptable; keep evidence free of keys and article text. Do not claim production readiness without that authorization and smoke evidence.

Implementation and phase completion records are complete. Keep this series Active in `plans/AGENTS.override.md` until provider authorization and the live compatibility smoke gate are resolved; then move it to Historical and retain the architecture links.

## Expected files

`app/templates/admin/editor.html`, `app/routes/admin/posts/editor.py`, `app/static/js/admin/editor.js` (optionally a new imported module), `app/static/css/admin.css`, `tests/test_ai_assist.py`, `tests/e2e/test_ai_assist.py`, relevant `architecture/`, `USAGE.md`, docs and agent overrides. **No migration.**

## Acceptance criteria

- [x] No-key installation has no visible AI UI or outbound provider traffic.
- [x] Suggestions are reviewable; no auto-overwriting, auto-saving or auto-publishing.
- [x] Manual/AI-applied tags share autosave, dirty and restoration semantics.
- [x] Errors, delays and stale requests do not lose user input.
- [x] Automated and browser tests pass.
- [ ] Permitted-use and real provider compatibility verified before deployment.

## Completion

**Status:** Implemented; provider-use approval and live smoke gate remain open.

Added conditional post-editor controls and an explicit review/apply flow that protects newer field edits, merges tags, and leaves persistence to normal Save. Existing draft autosave, recovery and dirty-state now include tags. Documentation and agent guidance describe external data transfer and provider limitations. Browser behavior uses a stubbed endpoint; no live provider request was made.

**Verification:** `pytest tests/test_ai_assist.py tests/test_author_role.py tests/config/test_ai_config.py tests/config/test_model.py tests/config/test_serialization.py tests/e2e/test_ai_assist.py -q` — 104 passed. `ruff check .`, `ruff format --check .`, dependency-manifest consistency and `npm run build` passed. Full suite: 4,879 passed, 53 failed, 21 skipped; failures were outside the AI-assist tests, in unrelated deployment/filesystem, storage/tasks, profile/webhook and theme areas. Mypy reports 17 errors across seven files; none are in the new AI service, route, or editor code (one is in the pre-existing config-model redaction helper).
