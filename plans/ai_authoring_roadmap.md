# Optional AI-Assisted Post Authoring — Roadmap

> **Plan status: ACTIVE — implementation complete; provider authorization and live compatibility gate remain open.** The three phases are implemented and documented under `architecture/`; do not enable editorial provider traffic until the gate is resolved.

**Date:** 2026-10-28
**Status:** Implementation complete; provider gate open
**Series prefix:** AIA
**Origin:** operator request for narrowly scoped editor-only TL;DR and taxonomy-aware tag suggestions.

## Goal

Add exactly two optional controls to the existing **post create/edit** editor: **AI write TL;DR** and **AI suggest tags**. Operate on current unsaved title and Markdown body; produce suggestions for author review. Normal post Save/Create remains the sole persistence path. With no configured provider key, neither button renders and no provider request can occur; otherwise the blog behaves identically.

Do not add chat, agents, auto-publishing, search, embeddings, RAG, migrations, queued tasks, public AI endpoints, or credentials in the CMS database.

## Verified integration points

- `app/routes/admin/posts/editor.py` owns new/edit post routes, `_render_editor()`, and Markdown preview.
- `app/templates/admin/editor.html` already provides `#summary` and `#tags` inputs, and the Markdown body macro.
- `app/static/js/admin/editor.js` is loaded for both routes by `app/static/js/main.js`; it already uses `csrfHeaders()`. Draft autosave, restore, and dirty-state now include tags alongside title/body/summary.
- `Post.summary` is limited to 500 characters. `Tag` is a flat vocabulary with unique `name` and `slug`. `app/routes/admin/helpers/tags.py` validates ASCII letters, numbers, spaces and hyphens, length <=50, and matches existing tags by `Tag.generate_slug()`.
- `app/config/` provides typed config, env precedence and secret redaction; `@author_required`, global CSRF checking, Flask-Limiter and `requests` are already in the project.

## Phases (execute in order)

| Phase | File | Deliverable | Status |
|---|---|---|---|
| 01 | [`ai_authoring_phase_01_provider_summary.md`](ai_authoring_phase_01_provider_summary.md) | Optional secret-safe provider config, authenticated bounded JSON endpoint, TL;DR | Implemented; provider-use approval/live smoke gate open |
| 02 | [`ai_authoring_phase_02_tag_reconciliation.md`](ai_authoring_phase_02_tag_reconciliation.md) | Candidate tags, deterministic existing-tag reuse, conditional second model pass | Implemented; mocked tests pass |
| 03 | [`ai_authoring_phase_03_editor_acceptance.md`](ai_authoring_phase_03_editor_acceptance.md) | Conditional UI, explicit review/apply, draft/dirty state, testing and documentation | Implemented; provider-use approval/live smoke gate open |

## Architecture and contracts

`post editor → POST /admin/ai-assist → app/services/ai_assist.py → authorized Go API → validated suggestion → editor review → normal Save`.

Proposed request body: `{"action":"summary|tags","title":"...","body":"...","post_id":123}`. `post_id` optional on new posts and must be checked for edit ownership. The server exclusively selects model, prompts, API key, and catalog; model responses are untrusted. Summary response: `{"suggestion":"..."}`. Tags response: `{"suggestions":["..."],"reused":["..."],"new":["..."]}`. No database writes, search index updates, or tag creation in the AI endpoint.

## Provider and policy gate

Initial proposed adapter: OpenCode Go using a server-side Console key, `glm-5.3-flash` model, and the Go OpenAI-compatible Chat Completions path `https://opencode.ai/inference/go/openai/v1/chat/completions`. Official references: https://opencode.ai/v2/docs/console/harnesses and https://opencode.ai/v2/docs/console/go. Requests need bearer authorization, stable `x-opencode-session` per authoring session and an identifying User-Agent. Pin a server-owned URL; do not expose a configurable arbitrary URL/SSRF surface.

**Deployment blocker:** OpenCode Go guidance says it is designed for coding-agent traffic. A blog summarization/tagging workflow may not qualify. Obtain provider authorization before enabling Go for this use. If disallowed, retain the optional feature but swap to a separately authorized pay-as-you-go or compatible API; do not disguise editorial traffic as coding-agent traffic. Verify model/endpoint/response shape before production use.

## Shared safety and acceptance

- No-key installations remain fully functional; buttons absent, endpoint fails closed, no external calls, no startup errors.
- All requests are POST, author/admin authenticated, CSRF-protected, per-user rate-limited, and input size/time bounded.
- Only the user click sends unsaved draft content to a third party; disclose that in the UI. Never log draft contents, catalog descriptions, credentials or raw provider errors.
- Summary is faithful, short, plain text and <=500 characters. Tag output is 3–5 valid, deduplicated names; no forced collapse of distinct concepts.
- Tag second pass only when unresolved candidates and existing relevant catalog entries exist; 2 provider calls maximum per tag action. No old post bodies are transmitted.
- All proposals are reviewed by the author before field changes and persisted only on normal Save.
- CI uses mocked provider responses; tests cover missing keys, auth, CSRF, privacy, normalization, malformed output, latency, failure and editor interactions.
- Implementation, architecture docs and phase completion records are complete. Keep this series Active until the provider authorizes editorial use (or an authorized alternate is selected) and the live compatibility smoke gate is completed.

## Completion

**Status:** Implementation complete; provider-use approval and live compatibility smoke gate remain open.

Implemented phases 01–03: secret-safe optional config, bounded authenticated summary/tag inference, privacy-safe deterministic/semantic tag reconciliation, conditional review/apply editor controls, tag-aware drafts/dirty state, tests, architecture and operator guidance. Provider requests in CI are mocked. No live OpenCode request was made because its documented coding-agent-use policy does not establish permission for editorial summarization/tagging. Keep AI disabled for editorial traffic until OpenCode explicitly permits it or an authorized alternate provider is selected; run a live smoke only after that gate is approved.

**Verification:** Focused AI/config/author/E2E suite: 104 passed. `ruff check .` passed; `ruff format --check .` passed (416 files); dependency-manifest consistency passed; `npm run build` passed. Full suite: 4,879 passed, 53 failed, 21 skipped, with failures in unrelated deployment/filesystem, storage/tasks, profile/webhook and theme areas; none were in the AI-assist tests. Mypy reports 17 errors across seven files; none are in the new AI service, route, or editor code (one is in the pre-existing config-model redaction helper). `git diff --check` passed.
