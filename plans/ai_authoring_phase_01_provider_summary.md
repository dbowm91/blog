# AI Authoring Phase 01 — Optional Provider, Authenticated Endpoint, TL;DR

> **Plan status: IMPLEMENTED — default-off and local OpenAI-compatible use supported.** The OpenCode Go provider's own usage policy remains a separate gate; it does not block the local compatible provider. See [roadmap](ai_authoring_roadmap.md), `architecture/routes/admin-routes.md`, and `architecture/services/overview.md`.

**Date:** 2026-10-28
**Status:** Implemented; model must be explicitly configured; local compatible provider works without a key
**Phase:** AIA-01
**Prerequisites:** None

## AIA-01A — Feature and configuration gate

Add `AiConfig` to `app/config/model.py` and `DevLogConfig.ai`. The provider defaults to `openai_compatible`, the base URL to loopback, and the model to an empty string; the feature is unavailable until an operator explicitly configures a model. OpenAI-compatible local servers require no API key. OpenCode Go uses its supported model and `OPENCODE_GO_API_KEY`, accepted **only via the server environment/.env**, not nonempty TOML or client requests. Wire `[ai]` through `app/config/loader.py`, its env override map and secret handling, `app/config/validation.py`, and `config.toml.example`. Include `api_key` in the canonical `SECRET_FIELDS` and check `app/config/secrets.py`, `app/config/serialization.py`, CLI config inspection, diagnostics and dataclass repr so no unredacted key can appear. Tests should verify redacted and raw serialization interfaces do not leak to user-visible surfaces.

Availability predicate = recognized provider + usable explicitly configured model, plus a key only for providers that require one. Missing configuration is not an installation error. Server-generated `ai_assist_available` decides template rendering; the server independently refuses direct calls when unavailable. Never contact the provider on startup or GET. Do not alter `SiteSettings` or API-token authentication.

The compatible provider accepts an operator-configured base URL and validates it as a safe HTTP(S) URL; local inference is the documented default endpoint but requires an explicitly set model. OpenCode Go uses its pinned server-owned endpoint and provider-specific request/response behavior. Keep Go usage policy separate from the local compatible adapter.

## AIA-01B — Small remote request service

Add `app/services/ai_assist.py` containing the only provider HTTP client and prompt/response validation. Use existing `requests` dependency; do not add SDKs or frameworks. Send `Authorization: Bearer` from server config, JSON content type, distinct User-Agent, and a stable random `x-opencode-session` stored in the authenticated Flask session across related authoring requests. No author ID, draft content or secret in that header. Limit output tokens and response bytes, connect timeout ~3s, read timeout ~20s; do not stream or allow tool calls. No automatic retries that could double bill.

Handle upstream 401/403/429/5xx, connect/read timeouts, malformed JSON, absent/invalid `choices`, non-text outputs and overlong responses as controlled errors. Strip provider details from client errors and logs; telemetry can record request ID, status class, duration and outcome only. Prompt instructions treat title/body as **untrusted source text**, not instructions to obey.

Provider-specific request parameters and JSON response mode must be verified via a permissioned manual smoke test and robust parser; unsupported parameters must not break normal authoring.

## AIA-01C — Post-editor-only endpoint

Register `POST /admin/ai-assist` with the admin blueprint in `app/routes/admin/posts/editor.py` or adjacent post-edit module. Use `@author_required` and existing global CSRF validation; never put it under the public `api` blueprint or exempt CSRF. Validate strict JSON object with `action="summary"` initially, title string <=200, nonempty UTF-8 body bounded to e.g. 64 KiB, optional integer `post_id`, and reject unknown/disallowed action/payload shape with 4xx. For edits, check `post_id` ownership identically to `edit_post()`. Do not impose a default application-side rate limit; retain the optional per-user limit setting for deployments with a concrete need. Use only submitted unsaved text, and make no provider request on failed validation/authorization/unavailable configuration. Do not fetch stored article content in place of submitted text.

Use an explicit response schema: `{"suggestion":"..."}`; return JSON errors with appropriate 4xx/5xx codes. Avoid logging user-provided inputs.

## AIA-01D — Summary specification

Generate an original, faithful, factual, **plain-text** 1–2 sentence TL;DR based on submitted title and Markdown body. Target ~150–300 chars, maximum 500 (`Post.summary`). No invented claims, HTML, Markdown preambles, vague promotion, fabricated links or invisible control characters. Reject empty, invalid or over-limit output. The service must never mutate `Post`, `Tag`, revision history, cache or FTS. The editor UI applies only after human acceptance in Phase 03.

## Tests and acceptance

Add `tests/test_ai_assist.py` and `tests/config/test_ai_config.py`. Mock all remote requests in automated tests. Cover default-off/feature hidden, explicit local compatible model with no API key, env precedence, illegal key in TOML, redaction (including serialization/diagnostics), author/admin and another-author-post access, CSRF, invalid JSON and bounds, unlimited default plus optional per-user limits, no outbound on validation failure, valid summary, empty/oversize output, upstream HTTP failures/timeouts, no DB writes after success/failure. Confirm public API key alone does not access this session route. Follow `tests/AGENTS.override.md` for fixtures.

- [x] Config and diagnostics safe; default-off state is invisible, while an explicitly configured local-compatible provider works without a key.
- [x] Endpoint restricted to permitted authors, CSRF checked, app-side throttling optional and unlimited by default.
- [x] Provider request bounded, honest failures, no implicit persistence.
- [x] Deterministic mocked tests pass.
- [ ] OpenCode Go provider usage separately authorized before enabling that adapter for editorial traffic.

## Expected files

`app/config/model.py`, `loader.py`, `validation.py`, secret/serialization files as needed, `.env.example`, `config.toml.example`, `app/services/ai_assist.py` (new), `app/routes/admin/posts/editor.py`, `tests/test_ai_assist.py` and `tests/config/test_ai_config.py` (new).

## Completion

**Status:** Implementation complete; local-compatible path is available after explicit opt-in; OpenCode Go usage gate remains provider-specific.

Implemented env-only provider-key handling with redaction, default-off availability, authenticated/CSRF-protected post-editor endpoint, ownership checks, optional per-user throttling (unlimited by default), bounded provider I/O and validated plain-text summaries. Explicitly configured local OpenAI-compatible servers work without an API key. Provider behavior is covered by mocks; no key or draft content was sent to OpenCode. The published Go guidance describes coding-agent use, so editorial authorization remains unverified for that adapter only.

**Rate-limit design decision:** Provider-owned quotas/abuse controls are authoritative for hosted providers; local model operators control their own capacity. Low app limits such as 12/hour disrupt ordinary human authoring and provide negligible protection for short bounded calls. Keep app-side throttling available only as opt-in configuration; do not ship a low default. If a future preset requires a ceiling, it must be at least 1,000 requests per user per hour, which is beyond realistic human use while remaining negligible for these bounded requests. The request/input/output/time limits and maximum provider calls per action remain enforced independently.

**Verification:** The focused AI/config/author/E2E suite passes locally (62 passed, 2 skipped). The dedicated [hosted AI authoring job](https://github.com/dbowm91/blog/actions/runs/40819498653/job/123268378537) also passed (62 passed, 2 skipped) on commit `53f3790`. The encompassing workflow remains failed only at the unrelated general mypy baseline; see the [roadmap](ai_authoring_roadmap.md) for the separate failure record and historical full-suite baseline.
