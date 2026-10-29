# Optional AI-Assisted Post Authoring — Roadmap

> **Plan status: IMPLEMENTED — AI is default-off and local-compatible opt-in works.** The three phases are implemented and documented under `architecture/`. The OpenCode Go editorial-use restriction is specific to that adapter and does not block local OpenAI-compatible inference.

**Date:** 2026-10-28
**Status:** Implemented; model blank by default; local OpenAI-compatible provider can be explicitly configured without a key
**Series prefix:** AIA
**Origin:** operator request for narrowly scoped editor-only TL;DR and taxonomy-aware tag suggestions.

## Goal

Add exactly two opt-in controls to the existing **post create/edit** editor: **AI write TL;DR** and **AI suggest tags**. Operate on current unsaved title and Markdown body; produce suggestions for author review. Normal post Save/Create remains the sole persistence path. By default the model is blank, neither button renders, and no provider request can occur. Configuring a local OpenAI-compatible model explicitly enables the feature without requiring an API key; otherwise the blog works identically without AI.

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
| 01 | [`ai_authoring_phase_01_provider_summary.md`](ai_authoring_phase_01_provider_summary.md) | Default-off, secret-safe provider config, authenticated bounded JSON endpoint, TL;DR | Implemented; local-compatible provider tested without a key; OpenCode Go policy is adapter-specific |
| 02 | [`ai_authoring_phase_02_tag_reconciliation.md`](ai_authoring_phase_02_tag_reconciliation.md) | Candidate tags, deterministic existing-tag reuse, conditional second model pass | Implemented; mocked tests pass |
| 03 | [`ai_authoring_phase_03_editor_acceptance.md`](ai_authoring_phase_03_editor_acceptance.md) | Conditional UI, explicit review/apply, draft/dirty state, testing and documentation | Implemented; default-off/local-compatible opt-in documented |

## Architecture and contracts

`post editor → POST /admin/ai-assist → app/services/ai_assist.py → explicitly configured local-compatible or authorized remote endpoint → validated suggestion → editor review → normal Save`.

Proposed request body: `{"action":"summary|tags","title":"...","body":"...","post_id":123}`. `post_id` optional on new posts and must be checked for edit ownership. The server exclusively selects model, prompts, API key, and catalog; model responses are untrusted. Summary response: `{"suggestion":"..."}`. Tags response: `{"suggestions":["..."],"reused":["..."],"new":["..."]}`. No database writes, search index updates, or tag creation in the AI endpoint.

## Provider and policy gate

The default compatible endpoint is the operator's loopback OpenAI-compatible server; the blank model keeps it inactive until configured. The compatible base URL is operator-controlled and validated; local use needs no credential. A remote compatible service may require `AI_API_KEY`, which is stored outside TOML. No call occurs until the author clicks an action.

**OpenCode Go adapter-specific gate:** The Go adapter uses a server-side Console key, supported model routing, and a fixed provider endpoint. Official references: https://opencode.ai/v2/docs/console/harnesses and https://opencode.ai/v2/docs/console/go. Its published guidance describes coding-agent use, so do not enable Go for editorial use unless the provider explicitly permits it. This restriction does not block the local-compatible adapter or default-off feature.

## Shared safety and acceptance

- Default installations remain fully functional without AI; blank model means buttons absent, endpoint fails closed, no provider calls, and no startup errors.
- All requests are POST, author/admin authenticated, CSRF-protected, and input size/time bounded. Application-side rate limiting is unlimited by default and remains an optional per-user operator setting.
- Only the user click sends unsaved draft content to the configured model endpoint (which may be local); disclose this in the UI. Never log draft contents, catalog descriptions, credentials or raw provider errors.
- Summary is faithful, short, plain text and <=500 characters. Tag output is 3–5 valid, deduplicated names; no forced collapse of distinct concepts.
- Tag second pass only when unresolved candidates and existing relevant catalog entries exist; 2 provider calls maximum per tag action. No old post bodies are transmitted.
- All proposals are reviewed by the author before field changes and persisted only on normal Save.
- CI uses mocked provider responses; tests cover default-off behavior, keyless local-compatible requests, auth, CSRF, privacy, normalization, malformed output, latency, failure and editor interactions.
- Implementation, architecture docs and phase completion records are complete. The local-compatible opt-in path does not require a live external provider gate. Keep OpenCode Go disabled for editorial use until its policy is explicitly verified.

## Completion

**Status:** Implemented; AI defaults off; local OpenAI-compatible provider works after explicit model configuration without a key. The OpenCode Go adapter remains policy-gated for editorial use.

Implemented phases 01–03: secret-safe default-off config, bounded authenticated summary/tag inference, privacy-safe deterministic/semantic tag reconciliation, conditional review/apply editor controls, tag-aware drafts/dirty state, tests, architecture and operator guidance. Provider requests in CI are mocked. A local server needs no credential; no AI request occurs until a model is configured and an author clicks a control. No live OpenCode request was made because its documented coding-agent-use policy does not establish permission for editorial summarization/tagging.

**Rate-limit decision:** The application imposes no AI rate limit by default; optional per-user limits remain for concrete deployment use cases. Hosted providers are expected to enforce their own quotas; local operators control local capacity. Low limits such as 12/hour block normal use and do not meaningfully protect providers for short bounded calls. If a future product preset ships a ceiling, require at least 1,000 requests/user/hour (ordinary human use cannot reach it and bounded-call cost remains negligible). Input/output byte caps, timeouts, and max calls/action remain the app's resource boundaries.

**Verification and hosted runs:** The pre-fix hosted `Tests` run is [`40814686905`](https://github.com/dbowm91/blog/actions/runs/40814686905). Its `AI authoring focused tests` job had one flaky E2E failure: the test read restored tags before the dynamically loaded editor finished recovery. The separate general `test` job failed at its existing mypy baseline; see “Unrelated repository baseline” below. A passing post-fix hosted AI run will be recorded here when available.

**Unrelated repository baseline (separate from AI):** The latest pre-fix hosted general `test` job failed at `mypy app` with 15 errors in nine existing files: `app/config/model.py`, `app/config/secrets.py`, `app/themes/translate.py`, `app/config_legacy.py`, `app/tag_cache.py`, `app/cli.py`, `app/services/operations/database.py`, `app/context_processors.py`, and `app/services/operations/doctor.py`. Its coverage-test step was skipped after mypy failed. The historical full-suite baseline is 4,879 passed, 53 failed, 21 skipped; failures were in deployment/filesystem, storage/tasks, profile/webhook and theme areas, not AI. These unrelated failures are not represented as AI failures and are not addressed by this change.
