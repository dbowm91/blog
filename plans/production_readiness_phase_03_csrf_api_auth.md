# Phase 3: CSRF, API Authentication, and POST Semantics

## Objective

Make POST request protection correct and predictable across browser forms and token-authenticated REST API calls. Browser-session form mutations must remain CSRF-protected. API-key JSON writes must not require browser-session CSRF tokens. No route should accidentally validate and consume the same CSRF token twice.

## Problems to Address

The app currently performs CSRF validation globally for every POST request in `create_app()` and also calls `validate_csrf_token()` manually in some POST routes. The CSRF implementation consumes a submitted token and rotates a new one after a successful validation. Therefore, a route that is covered by both global validation and manual validation can fail on the second check.

The REST API uses `X-API-Key` authentication, but POST API endpoints still pass through the global CSRF hook before route-level API authentication. This likely makes normal JSON clients unable to create or update resources unless they also have a Flask session and CSRF token, which is not appropriate for API-key authentication.

## Scope

This phase covers CSRF architecture, API-key route exemption, route-level cleanup, and regression tests. It does not redesign API authentication or add OAuth/JWT.

## Design Principles

CSRF is for browser-session authority. API-key requests are bearer-token requests and should be protected by token secrecy, HTTPS, scopes, rate limits, and audit logging, not browser CSRF tokens.

A given request should have exactly one CSRF validation path. Do not validate globally and then again inside the route.

CSRF exemptions should be explicit and narrow. Do not disable CSRF globally for all POSTs.

## Implementation Steps

1. Inventory every manual `validate_csrf_token()` call.

   Search the codebase for `validate_csrf_token`. Categorize each call as:

   - Browser form route already covered by global POST hook.
   - API route that should be exempt from CSRF and protected by API key.
   - Special route that needs explicit custom behavior.

2. Choose the final CSRF architecture.

   Preferred architecture:

   - Keep global `before_request` CSRF validation for browser form POSTs.
   - Add explicit skip conditions for API routes and any webhook-style endpoints that use non-session authentication.
   - Remove route-local duplicate calls for routes covered by the global hook.
   - Keep tests proving browser POSTs still require CSRF.

   Alternative architecture:

   - Remove global POST validation.
   - Add decorators or explicit calls to all browser form mutation routes.

   The preferred architecture is less invasive, but only if the exemption logic is clear and well-tested.

3. Implement a narrow exemption predicate.

   Add a helper such as:

   ```python
   def should_skip_csrf() -> bool:
       if req.blueprint == "api":
           return True
       return False
   ```

   If endpoint naming is more reliable than blueprint, use `req.endpoint.startswith("api.")`. Do not exempt based only on content type, because browser forms can submit JSON and public routes might still require CSRF.

4. Remove duplicate manual validations.

   For browser form routes like logout and comment submission, remove `validate_csrf_token()` if the global hook covers them. Keep route code focused on business validation.

   If any route must validate manually because it is intentionally skipped globally, document why next to the route or helper.

5. Ensure login and reset flows are covered intentionally.

   Admin login, 2FA verification, password reset, forgot-password, and 2FA setup/disable are browser POSTs. Confirm templates include CSRF tokens and tests exercise missing-token rejection where appropriate.

6. Make API POST behavior explicit.

   Ensure `POST /api/posts`, `PUT /api/posts/<id>`, `DELETE /api/posts/<id>`, subscriber mutations, tag/page/series mutations, and stats/admin API actions use API key/scope authentication as their authority check and do not require CSRF.

7. Revisit scoped API token enforcement.

   The API auth module has `require_scope`, but some endpoints may use only `require_api_key`. Inventory write endpoints and decide whether scoped tokens should be enforced before public release. At minimum, document current behavior honestly. Prefer adding `require_scope` to write endpoints that correspond to existing scope names.

8. Add negative and positive regression tests.

   Tests must catch both accidental over-protection and under-protection.

## Tests to Add or Update

Browser CSRF tests:

- POST logout with a valid CSRF token succeeds.
- POST logout with missing/invalid CSRF token returns 403.
- POST public comment with valid CSRF succeeds or redirects as expected.
- POST public comment with missing CSRF returns 403.
- POST admin mutation route with missing CSRF returns 403.

API tests:

- POST `/api/posts` with valid `X-API-Key` and JSON body succeeds without `X-CSRF-Token`.
- POST `/api/posts` without API key returns 401.
- POST `/api/posts` with invalid API key returns 401.
- PUT and DELETE API routes behave the same way.
- If scoped tokens are enforced, missing scope returns 403.

Double-validation regression tests:

- A route previously calling `validate_csrf_token()` manually must not fail because of token consumption after global validation.

## Verification Commands

```bash
ruff check .
ruff format --check .
mypy app
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ -v --ignore=tests/e2e -k "csrf or api or comment or logout"
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ -v --ignore=tests/e2e --cov=app --cov-fail-under=80
```

Manual API smoke:

```bash
export API_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
# Start the app with valid SECRET_KEY and ADMIN_PASSWORD.
curl -i -X POST http://localhost:5000/api/posts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"title":"API Smoke","body":"hello","published":false}'
```

## Acceptance Criteria

No browser form POST is left unintentionally unprotected. No API-key JSON endpoint requires a browser CSRF token. Routes covered by global CSRF validation do not perform a second validation. Regression tests prove the intended behavior for both browser and API POSTs.

## Risks

Over-broad CSRF exemptions can weaken admin protection. Keep exemption logic tied to API blueprint or known non-session endpoints. Do not exempt `/admin/*` based on JSON content type alone. Avoid hiding CSRF failures in tests by globally setting `CSRF_ENABLED=False` except in narrowly scoped tests that are not about CSRF.
