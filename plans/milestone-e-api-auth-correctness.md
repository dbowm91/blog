# Milestone E Plan: API Authorization Correctness

## Objective

Make REST API token authorization semantics correct, deterministic, documented, and safe for public-release integrations.

The API currently defines a set of scopes including `admin:*`, but the `require_scope()` decorator checks only exact scope membership. As a result, a token with `admin:*` does not satisfy `posts:read`, `posts:write`, `subscribers:read`, or other scoped route checks unless those exact scopes are also present. This is a correctness bug and a documentation hazard for any public API.

This milestone should define scope matching semantics, implement them centrally, preserve legacy API key compatibility, and add focused tests.

## Current behavior to review

Primary file:

- `app/routes/api/auth.py`

Current relevant behavior:

- `API_KEY` from the environment acts as a legacy key and grants all scopes.
- Scoped API tokens are stored as SHA-256 hashes in the database.
- `ApiToken.is_valid()` determines whether a token can be used.
- `require_api_key()` accepts either the legacy key or a scoped token.
- `require_scope(scope)` currently checks `scope in auth_info["scopes"]`.
- `SCOPES` includes exact scopes and `admin:*`.

Likely additional files:

- `app/models.py` for `ApiToken`.
- API route modules under `app/routes/api/`.
- Admin route/UI code for creating API tokens, if present.
- `docs/openapi.yaml`.
- README/DEPLOY/API docs.
- Tests for API auth and API endpoints.

## Target semantics

Implement explicit scope matching with fail-closed behavior.

Recommended semantics:

1. Exact scope match grants access.
2. `admin:*` grants access to every API scope.
3. Optional category wildcard grants access to scopes in that category, e.g. `posts:*` grants `posts:read` and `posts:write`.
4. Unknown scopes do not grant access.
5. Empty scope lists do not grant access.
6. Legacy `API_KEY` preserves current behavior and grants all scopes.

If category wildcards are not desired, support only `admin:*` and exact matches. If category wildcards are supported, add the wildcard values to `SCOPES` or validate them in a helper.

## Implementation steps

### Step 1: Add a central scope-matching helper

In `app/routes/api/auth.py`, add a helper such as:

```python
def scope_allows(granted_scopes: list[str], required_scope: str) -> bool:
    if not required_scope:
        return False
    if "admin:*" in granted_scopes:
        return True
    if required_scope in granted_scopes:
        return True
    if ":" in required_scope:
        category, _action = required_scope.split(":", 1)
        if f"{category}:*" in granted_scopes:
            return True
    return False
```

Harden it against malformed values:

- Normalize to a set of strings.
- Ignore non-string values if scopes are loaded from JSON.
- Do not treat `*` alone as valid unless deliberately added.
- Do not use prefix matching such as `startswith`, because `post:*` should not satisfy `posts:read`.

### Step 2: Update `require_scope()`

Replace exact membership check with the helper.

Preserve response behavior:

- Missing/invalid auth returns 401.
- Authenticated but insufficient scope returns 403.
- Error message can remain `Missing scope: <scope>`.

Recommended:

```python
if not scope_allows(auth_info.get("scopes", []), scope):
    return jsonify({"error": f"Missing scope: {scope}"}), 403
```

### Step 3: Validate `SCOPES` registry

Review the existing `SCOPES` set.

If category wildcards are supported, add:

- `posts:*`
- `media:*`
- `subscribers:*`
- `tags:*`
- `pages:*`
- `series:*`
- `analytics:*` if needed
- `newsletter:*` if needed

Alternatively, leave only `admin:*` as the global wildcard and require exact scopes for all other categories.

The project should decide which model is easier for admins. For a self-hosted CMS, category wildcards are useful and intuitive.

### Step 4: Review token creation UI/API

Find admin/API-token creation surfaces and ensure they present scopes consistently.

Tasks:

- Ensure `admin:*` is described as full API access.
- If category wildcards are supported, expose them clearly.
- Prevent duplicate scopes from causing UI noise.
- Ensure stored scopes are a list of strings.
- Ensure malformed scope values are rejected at creation time if token creation code exists.

### Step 5: Add tests for scope matching helper

Add unit tests for `scope_allows()`.

Cases:

- `posts:read` allows `posts:read`.
- `posts:write` does not allow `posts:read`.
- `admin:*` allows every known required scope.
- `posts:*` allows `posts:read` and `posts:write` if category wildcard support is enabled.
- `posts:*` does not allow `pages:read`.
- `post:*` does not allow `posts:read`.
- Empty granted scopes deny.
- Unknown granted scopes deny.
- Malformed granted scopes deny.
- Non-string values do not crash the helper.

### Step 6: Add request-level API auth tests

Add integration tests using the Flask test client.

Minimum cases:

1. No API key returns 401.
2. Invalid API key returns 401.
3. Legacy `API_KEY` succeeds on a scoped endpoint.
4. Scoped token with exact required scope succeeds.
5. Scoped token missing required scope returns 403.
6. Scoped token with `admin:*` succeeds on multiple endpoints.
7. Expired token returns 401.
8. Revoked/invalid token returns 401.
9. Token `last_used_at` updates on successful use.
10. If category wildcards are supported, `posts:*` succeeds on post read/write endpoints but fails on subscribers/pages endpoints.

Use existing app/test factories and database fixtures. Avoid leaking real token values into logs.

### Step 7: Update OpenAPI and docs

Update `docs/openapi.yaml` and any README/API documentation to describe:

- Header name: `X-API-Key`.
- Legacy API key behavior.
- Scoped API token behavior.
- Exact scopes.
- Wildcard semantics.
- Difference between 401 and 403.

Recommended wording:

"The legacy `API_KEY` environment variable grants full API access and is intended for simple single-user deployments. Scoped API tokens are preferred for integrations. A token with `admin:*` grants all API scopes. If category wildcards are enabled, a token with `posts:*` grants all post scopes but not subscriber, page, tag, analytics, or admin scopes."

### Step 8: Consider migration/backward compatibility

Existing tokens with exact scopes continue to work.

Existing tokens with `admin:*` become more capable in the way the scope registry already implies. This is technically a behavior change, but it corrects the intended semantics. Mention it in release notes if a changelog exists.

If category wildcards are newly added, ensure no existing malformed wildcard scopes unexpectedly grant broad access. Only known categories should match.

Optional stronger implementation:

```python
VALID_WILDCARD_SCOPES = {"admin:*", "posts:*", "media:*", ...}
```

Then `scope_allows()` only honors category wildcards in that allowlist.

## Security considerations

Fail closed on malformed data. The helper should never grant access because of a malformed required scope or a broad string-prefix match.

Do not use substring or prefix matching. Always split on `:` and compare category/action boundaries.

Do not make `*` or `*:*` valid unless there is a deliberate product decision to do so. `admin:*` is already clear enough as the global/full-access scope.

Avoid exposing token hashes or raw tokens in logs, UI, or test failure output.

## Validation commands

Run:

```bash
python -m pytest tests/ -k "api or token or scope" -v
python -m pytest tests/ --ignore=tests/e2e -v
ruff check app tests
ruff format --check app tests
mypy app/
```

If e2e/API smoke tests exist:

```bash
docker compose --profile production up -d --build
curl -i -H "X-API-Key: invalid" http://127.0.0.1:5000/api/posts
docker compose --profile production down -v
```

## Acceptance criteria

- `admin:*` satisfies all scoped API routes.
- Exact scopes continue to work.
- Missing scopes still fail with 403.
- Missing/invalid auth still fails with 401.
- Legacy `API_KEY` remains backward-compatible.
- Category wildcard behavior is either implemented and tested or explicitly not supported/documented.
- Tests cover helper-level and request-level auth behavior.
- OpenAPI/docs match runtime authorization semantics.

## Suggested commit scope

Keep this milestone focused on API authorization. Do not mix it with metrics, health, deployment topology, or database support changes unless tests need minor fixture adjustments.
