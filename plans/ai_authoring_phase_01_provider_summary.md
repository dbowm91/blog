# AI Authoring Phase 01 — Optional Provider, Authenticated Endpoint, TL;DR

> **Plan status: IMPLEMENTED — provider-use approval and live smoke gate remain open.** [Roadmap](ai_authoring_roadmap.md). Behavior is documented in `architecture/routes/admin-routes.md` and `architecture/services/overview.md`.

**Date:** 2026-10-28
**Status:** Implemented; provider-use approval and live smoke gate open
**Phase:** AIA-01
**Prerequisites:** None

## AIA-01A — Feature and configuration gate

Add `AiConfig` to `app/config/model.py` and `DevLogConfig.ai` with provider fixed to `opencode_go`, model default `glm-5.3-flash`, and blank API key default. Wire `[ai]` through `app/config/loader.py`, its env override map and secret handling, `app/config/validation.py`, and `config.toml.example`. Accept `OPENCODE_GO_API_KEY` **only via the server environment/.env**, not nonempty TOML or client requests. Include `api_key` in the canonical `SECRET_FIELDS` and check `app/config/secrets.py`, `app/config/serialization.py`, CLI config inspection, diagnostics and dataclass repr so no unredacted key can appear. Tests should verify redacted and raw serialization interfaces do not leak to user-visible surfaces.

Availability predicate = recognized provider + usable configured model + nonempty key. Missing key is not an installation error. Server-generated `ai_assist_available` decides template rendering; the server independently refuses direct calls with no key. Never contact the provider on startup or GET. Do not alter `SiteSettings` or API-token authentication.

A fixed server-owned Go endpoint should be used, not request-provided base URLs. Prefer `https://opencode.ai/inference/go/openai/v1/chat/completions` per current Console harness documentation. If support for other providers is needed later, add explicit adapters rather than arbitrary URLs.

## AIA-01B — Small remote request service

Add `app/services/ai_assist.py` containing the only provider HTTP client and prompt/response validation. Use existing `requests` dependency; do not add SDKs or frameworks. Send `Authorization: Bearer` from server config, JSON content type, distinct User-Agent, and a stable random `x-opencode-session` stored in the authenticated Flask session across related authoring requests. No author ID, draft content or secret in that header. Limit output tokens and response bytes, connect timeout ~3s, read timeout ~20s; do not stream or allow tool calls. No automatic retries that could double bill.

Handle upstream 401/403/429/5xx, connect/read timeouts, malformed JSON, absent/invalid `choices`, non-text outputs and overlong responses as controlled errors. Strip provider details from client errors and logs; telemetry can record request ID, status class, duration and outcome only. Prompt instructions treat title/body as **untrusted source text**, not instructions to obey.

Provider-specific request parameters and JSON response mode must be verified via a permissioned manual smoke test and robust parser; unsupported parameters must not break normal authoring.

## AIA-01C — Post-editor-only endpoint

Register `POST /admin/ai-assist` with the admin blueprint in `app/routes/admin/posts/editor.py` or adjacent post-edit module. Use `@author_required` and existing global CSRF validation; never put it under the public `api` blueprint or exempt CSRF. Validate strict JSON object with `action="summary"` initially, title string <=200, nonempty UTF-8 body bounded to e.g. 64 KiB, optional integer `post_id`, and reject unknown/disallowed action/payload shape with 4xx. For edits, check `post_id` ownership identically to `edit_post()`. Require server-side per-user rate limit (e.g. 12/hour shared by actions), and no external HTTP on failed validation/authorization/missing key. Do not fetch stored article content in place of submitted unsaved text.

Use an explicit response schema: `{"suggestion":"..."}`; return JSON errors with appropriate 4xx/5xx codes. Avoid logging user-provided inputs.

## AIA-01D — Summary specification

Generate an original, faithful, factual, **plain-text** 1–2 sentence TL;DR based on submitted title and Markdown body. Target ~150–300 chars, maximum 500 (`Post.summary`). No invented claims, HTML, Markdown preambles, vague promotion, fabricated links or invisible control characters. Reject empty, invalid or over-limit output. The service must never mutate `Post`, `Tag`, revision history, cache or FTS. The editor UI applies only after human acceptance in Phase 03.

## Tests and acceptance

Add `tests/test_ai_assist.py` and `tests/config/test_ai_config.py`. Mock all remote requests in automated tests. Cover key absent/feature hidden, env precedence, illegal key in TOML, redaction (including serialization/diagnostics), author/admin and another-author-post access, CSRF, invalid JSON and bounds, per-user rate limits, no outbound on validation failure, valid summary, empty/oversize output, upstream HTTP failures/timeouts, no DB writes after success/failure. Confirm public API key alone does not access this session route. Follow `tests/AGENTS.override.md` for fixtures.

- [x] Config and diagnostics safe, no-key state invisible and functional.
- [x] Endpoint restricted to permitted authors, CSRF checked, per-user rate limited.
- [x] Provider request bounded, honest failures, no implicit persistence.
- [x] Deterministic mocked tests pass.
- [ ] Provider usage separately authorized and live compatibility smoke test completed before deployment.

## Expected files

`app/config/model.py`, `loader.py`, `validation.py`, secret/serialization files as needed, `.env.example`, `config.toml.example`, `app/services/ai_assist.py` (new), `app/routes/admin/posts/editor.py`, `tests/test_ai_assist.py` and `tests/config/test_ai_config.py` (new).

## Completion

**Status:** Implementation complete; external provider gate open.

Implemented env-only `OPENCODE_GO_API_KEY` handling with redaction, fail-closed availability, authenticated/CSRF-protected post-editor endpoint, ownership checks, per-author throttling, bounded provider I/O and validated plain-text summaries. Provider behavior is covered by mocks; no key or draft content was sent to OpenCode. The published Go guidance describes coding-agent use, so editorial authorization and live compatibility remain unverified. Do not enable this provider for editorial drafts until explicitly permitted or replaced by an authorized adapter.

**Verification:** `pytest tests/test_ai_assist.py tests/test_author_role.py tests/config/test_ai_config.py tests/config/test_model.py tests/config/test_serialization.py tests/e2e/test_ai_assist.py -q` — 104 passed (includes all phases; latest run). `ruff check .` and `ruff format --check .` passed; dependency-manifest consistency and `npm run build` passed. Full suite: 4,879 passed, 53 failed, 21 skipped; failures are in unrelated deployment/filesystem, storage/tasks, profile/webhook and theme tests. No AI-assist test failed. Mypy reports 17 errors across seven files; none are in the new AI service, route, or editor code (one is in the pre-existing config-model redaction helper).
