# AI Authoring Phase 02 — Candidate Tags and Taxonomy Reconciliation

> **Plan status: IMPLEMENTED.** Requires [AIA-01](ai_authoring_phase_01_provider_summary.md). Behavior is documented in `architecture/services/tag.md`.

**Date:** 2026-10-28
**Status:** Implemented
**Phase:** AIA-02

## Goal and invariants

Add `action="tags"` to the same authenticated JSON route and inference service. Propose 3–5 topical tags for the unsaved article and prefer already established tags **only where semantically equivalent**. A similar or broader existing tag is not automatically a synonym. Retain new valid concepts when nothing matches.

Use `Tag.generate_slug()` and `validate_tag_name()` from `app/routes/admin/helpers/tags.py` as the authoritative canonicalization/validation rules: ASCII letters, digits, space, hyphen, <=50 characters. Existing `app/services/tag.py` must not grow a competing policy. Tag rows are only created/reused on the normal post save. No migration, embeddings, vector store, tag alias database, or AI writes.

## AIA-02A — First pass: candidate list

Send only current unsaved title/body and compact task instructions to a text model; parse structured JSON, e.g. `{"tags":["Python","FastAPI","Machine Learning"]}`. Output limited to 3–5 final tags (6 candidate max), short and discriminative. Reject unexpected structures/field types, empty responses, excessive count, fake JSON wrappers, overlong output or unsafe punctuation. Validate each tag with the existing helper; drop invalid candidates and deduplicate by `Tag.generate_slug()`. If none survive, return error without any field mutation.

The model must not select tag IDs or read prior articles at this stage; article text is untrusted prompt input. Keep provider call counts and output token budgets bounded.

## AIA-02B — Exact reuse before any second call

Query available tags via `db.session.execute(select(...))` and canonicalize matching slugs deterministically. Replace candidate casing/spelling with the persisted Tag name for exact matches. If **all** candidates match known tags, return immediately with no second call. If the catalog is empty, retain valid proposals and return immediately.

Only retrieve metadata the requesting role may know: publicly used tags and their published-post examples; administrators may access private taxonomy metadata, but do not send other authors' unpublished draft titles when a non-admin requests suggestions. Do not use `Tag.posts` lazy iteration as a basis for N+1 external disclosure.

## AIA-02C — Second pass only for unmatched proposals

Build a compact, bounded server-side catalog: tag ID, canonical name, published-post usage count and optionally one *short* representative **published** title. Prefer lexical/slug-related tags, then frequently used tags; deterministic sort and stable tie-breaking. Limit to approximately 80 entries and a strict serialized input budget; no complete historical post bodies, no unpublished post text, no per-post lists, and no remote access to the database.

Prompt the second model with only unresolved candidates and this catalog; do **not** resend the entire article. Require for each candidate either an existing **catalog tag ID** if meaning matches, or the original candidate marked `new`. Do not force every proposal into an existing tag. For example, `Deep Learning` does not automatically collapse to `Machine Learning`. Parse structured mapping output, verify IDs were supplied in the catalog and returned names come from the database, reject duplicate/conflicting resolutions, and deduplicate final tags by slug.

Provider may be called **at most twice per tag request**. If the second pass is unavailable, times out, returns malformed output or hallucinated IDs, discard the semantic mapping and return the first-pass candidate list after deterministic exact canonicalization. Never return partially validated or invented mappings.

## AIA-02D — Response contract

Return canonical display strings and reuse/new metadata: `{"suggestions":["Python","FastAPI"],"reused":["Python"],"new":["FastAPI"]}`. Validate again on post Save because the catalog may change between inference and persistence. Generated suggestions must not create Tag rows, modify Post relationships, invalidate tag cache or commit transactions.

## Tests

Extend `tests/test_ai_assist.py` with network stubs, query spying and DB assertions:

1. Empty database/catalog: exactly one provider call; no tag write.
2. Exact/case/slug matches: canonical names, no second call when fully resolved.
3. Mixed proposals: second call receives bounded catalog and only unmatched proposals, never previous bodies.
4. Known-equivalent tag ID yields persisted canonical name; unrelated tag remains new.
5. Hallucinated ID, duplicates, invalid strings, wrong types and overlong responses are rejected.
6. Second-pass timeout/429/malformed data returns deterministic first-pass fallback.
7. 80+ tags: stable selection, bounded prompt, usage-based priorities and no N+1.
8. Non-admin cannot leak another author's unpublished-only tag/title metadata.
9. No key/auth/CSRF/request validation failure reaches inference; all paths cause zero DB writes.

## Acceptance criteria

- [x] At most two calls; second skipped when pointless; no past post bodies sent.
- [x] Exact reuse deterministic and model mapping verified by existing IDs.
- [x] Meaningfully distinct new tag proposals retained.
- [x] Bounded catalog and role-safe privacy boundary.
- [x] Invalid or failed provider output never mutates tag data.
- [x] Tests cover failure fallback, taxonomy evolution and access boundaries.

## Expected files

`app/services/ai_assist.py`, `app/routes/admin/posts/editor.py`, `tests/test_ai_assist.py`. Consult but do not duplicate `app/models.py`, `app/routes/admin/helpers/tags.py` and `app/services/tag.py`.

## Completion

**Status:** Implemented.

Tag suggestions now validate against the existing tag policy, reuse exact persisted tags deterministically, and use a bounded role-safe catalog for conditional semantic reconciliation. The second pass receives only unresolved candidates and catalog metadata; failures fall back to first-pass candidates. No tag rows or post relationships are changed by inference.

**Verification:** The AI authoring/config/access/E2E suite passed: `pytest tests/test_ai_assist.py tests/test_author_role.py tests/config/test_ai_config.py tests/config/test_model.py tests/config/test_serialization.py tests/e2e/test_ai_assist.py -q` — 104 passed. All provider interactions were mocked.
