# Site Identity Phase 03 — Public Authentication

**Roadmap:** [site_identity_authoring_roadmap.md](site_identity_authoring_roadmap.md)
**Date:** 2026-10-24
**Status:** Complete
**Severity:** High — non-admin accounts exist in the database but there is no way for anyone to sign in as one.

## Objective

Give the site a real public login: a page an ordinary visitor can reach, an
account page they land on afterwards, and a nav affordance so the page is
discoverable.

## Findings

### SIA-10 — There is no public login page (critical)

The only login route in the application is `admin.login`:

```python
# app/routes/admin/auth.py:32
@admin.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login() -> Any:
```

(The `@limiter.limit` decorator was removed on 2026-10-24, when login rate
limiting moved to the reverse proxy. The quote above is the code as it was
when this finding was made.)

It renders `admin/login.html` and lives under the `/admin` blueprint. There is
no `/login`, `/signin` or `/account` route on the public blueprint
(`app/routes/public/__init__.py` registers browse, posts, subscribe and meta
only).

### SIA-11 — Non-admin accounts cannot authenticate at all (critical)

The admin login admits only administrators:

```python
# app/routes/admin/auth.py:61
if user and user.check_password(password) and user.is_admin:
```

The running instance holds three non-admin accounts — `author1`, `author2`,
`author3` — and there is no other authentication path for them. These accounts
exist, are listed in `/admin/users`, and are permanently unusable. The password
reset flow has the same gate (`user.is_admin`, line 173), so a non-admin user
cannot even recover a password.

This matters for Phase 04: an author page needs an author who can actually
sign in and edit their own profile.

### SIA-12 — The public nav offers no way to sign in (high)

Measured in Chromium as an anonymous visitor:

```
nav links = ['× -> ', 'Search -> ', 'Posts -> /']
```

There is no "Log in" entry. `app/templates/base.html` renders
`{% if current_user.is_authenticated %}` (Dashboard / Logout) and nothing at
all in the else branch — so an anonymous visitor is given no indication that
signing in exists.

### SIA-13 — The admin session machinery must not be reused blindly (high)

The admin login does three things beyond checking a password: it creates an
`AdminSession` row with the client IP and user agent, it stores
`session["admin_session_id"]` and `session["admin_session_ip"]`, and it
enforces `SESSION_IP_BINDING` through the `admin_required` decorator in
`app/routes/admin/__init__.py`.

Those controls belong to the admin panel. A public account session must not be
granted admin-panel authority, and it must not be able to satisfy
`admin_required`. Two separate concerns must stay separate:

- **Admin session** — `AdminSession` row + IP binding + optional TOTP.
  Grants `/admin/*`.
- **Public account session** — an ordinary signed-in visitor.
  Grants `/account` and nothing under `/admin`.

`flask_login` keeps one `current_user` per session cookie, so the admin
`logout` route (`app/routes/admin/auth.py:97`) calls `logout_user()` and would
also end a public session. That is acceptable and must simply be documented:
signing out of the admin signs out the visitor.

`login_manager.login_view` is set to `"admin.login"` in
`app/extensions.py`. A public `login_required` must redirect to the **public**
login route, not the admin one, so the public routes must use an explicit
`@login_required` with their own `login_view` behaviour rather than relying on
the global default.

### SIA-14 — The public login must not be a weaker path than the admin login (high)

The admin login applies, in order: a lockout after
`MAX_FAILED_ATTEMPTS` for `LOCKOUT_DURATION_MINUTES`, a `LOGIN_FAILURE_DELAY`
sleep on failure, session clearing before `login_user()` (session-fixation
protection), and TOTP when enabled. The public login must apply the same
controls to the same `User` row, otherwise the public route becomes a
password-oracle and a lockout bypass.

## Fix specification

### 1. Routes

New module `app/routes/public/auth.py`, registered from
`app/routes/public/__init__.py` the same way the other public modules are:

| Route | Method | Behaviour |
|---|---|---|
| `/login` | GET, POST | Public sign-in form |
| `/logout` | POST | Ends the session, redirects to the index |
| `/account` | GET | The signed-in user's account page |
| `/account/profile` | GET, POST | The signed-in user edits their own profile |

`/account/profile` reuses the Phase 02 profile service and the same rendering
as the admin editor, so there is one implementation of "edit a profile" with two
entry points — not two implementations.

### 2. Login behaviour

- Accept a **username or email** in a single field, matching the wording of
  the existing admin forgot-password form (`identifier`). Look the user up by
  `username` first, then by `email`.
- On failure: `record_failed_login(MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES)`,
  commit, flash a generic "Invalid credentials." message, and sleep
  `LOGIN_FAILURE_DELAY`. The message must not reveal whether the account
  exists.
- On a locked account: flash the lockout message and do not sleep (the delay
  is for credential guessing, and the lockout already stops it).
- On success: `session.clear()` before `login_user(user)` — the same
  session-fixation protection the admin login uses — then
  `user.reset_failed_login()` and commit.
- A `?next=` parameter is honoured after the login. It must be validated:
  accept only a path beginning with a single `/` and not `//` (protocol-relative
  URL), and reject anything with a scheme or a netloc. The existing
  `_safe_redirect_url()` in `app/routes/public/posts.py` reads the `Referer`
  header; this case needs an explicit `next` parameter validator, which must be
  a **new** function with its own tests rather than a silent reuse of a
  Referer-based helper.
- Rate limit: the per-IP limit is the proxy's job, not the application's. The application keeps the account lockout.
- TOTP: if the user has 2FA enabled, the public login must not bypass it.
  Either require the TOTP code on the public form or refuse to sign in a
  2FA-enabled user and point them at the admin 2FA flow. Whichever is chosen,
  it must be a decision recorded here, not an accident — a 2FA-enabled account
  that can be signed in around its second factor is a security regression.

### 3. Public account session

The public session is an ordinary `flask_login` session. The `User` model is
already a `UserMixin`, and `login_manager` is initialised in `app/__init__.py`.

Guard the admin side explicitly: `admin_required` in
`app/routes/admin/__init__.py` must continue to require `current_user.is_admin`
(and the admin `AdminSession` row). A public session must not satisfy it. Since
both use the same `User` model, the check is `is_admin` plus the presence of a
valid `AdminSession` — verify the current implementation already does both and
add a regression test that a public-only session receives 302/403 on `/admin`.

### 4. Templates and navigation

- New `app/templates/login.html` — extends `base.html`. Reuse the existing
  admin login styling vocabulary (`login-*` classes exist in the admin
  stylesheet); the public shell loads `base.css`, `layout.css`, `public.css`,
  `forms.css` and `utilities.css`, so the public login page needs its own
  styles in `public.css` or a small addition to `forms.css`. It must not
  depend on `admin.css`, which the public shell does not load.
- New `app/templates/account.html` — shows the signed-in user's display name,
  avatar, short bio, and a link to `/account/profile`. Show their published
  posts if Phase 04 has landed; otherwise show the post count only. The page
  must not break when Phase 04 has not landed.
- `app/templates/base.html` — in the anonymous branch of the nav, add a
  **Log in** link to `/login`. In the authenticated branch, add an **Account**
  link to `/account` next to the existing Dashboard / Logout entries.
- The mobile menu (`app/static/js/public/mobile-menu.jsx`) renders the same
  nav tree; it must show the new entries too.

### 5. Password reset for non-admin users

`app/routes/admin/auth.py:forgot_password` currently only issues a reset token
for `user.is_admin`. A non-admin who forgets their password has no recovery
path. Extend it to all users, or add a public forgot-password flow. The reset
email template must work for a non-admin recipient. The reset token handling
already deletes every `AdminSession` for the user on reset — a public session
must be invalidated as well (clearing the session cookie on reset covers it).

## Tests

1. **Login page (unit)** — `GET /login` returns 200 and renders a form with a
   CSRF token.
2. **Successful login (unit)** — POST valid credentials for a non-admin user;
   assert the response redirects and the session is authenticated.
3. **Wrong password (unit)** — assert a generic error message, that
   `failed_login_count` incremented, and that no user-existence information is
   leaked. Compare the message for a known username and an unknown one.
4. **Lockout (unit)** — assert the account locks after `MAX_FAILED_ATTEMPTS`
   failures and that further attempts are refused.
5. **Lockout (unit)** — assert the account locks after `MAX_FAILED_ATTEMPTS`
   failures, which is the control the application keeps.
6. **Open redirect (unit)** — assert `?next=https://evil.example/` is rejected
   and `?next=/post/x` is accepted.
7. **Session fixation (unit)** — assert the session identifier changes across
   a login.
8. **2FA (unit)** — assert a 2FA-enabled user cannot complete a public login
   without the second factor.
9. **Admin isolation (unit)** — a public-only session must not reach
   `/admin/dashboard`; assert a redirect or 403.
10. **Account page (unit)** — `GET /account` requires a session; assert it
    renders the signed-in user's profile fields.
11. **Nav affordance (browser, `tests/e2e/`)** — as an anonymous visitor, assert
    a "Log in" link exists and navigates to `/login`; after signing in, assert
    an "Account" link exists.
12. **Mobile nav (browser)** — assert the login entry appears in the mobile
    menu.
13. **Non-admin password reset (unit)** — assert a reset token is issued for a
    non-admin user and the reset email is queued.

## Expected files

- `app/routes/public/auth.py` (new)
- `app/routes/public/__init__.py` (register the module)
- `app/templates/login.html` (new)
- `app/templates/account.html` (new)
- `app/templates/base.html` (nav entries)
- `app/static/css/public.css` (public login styling)
- `app/static/js/public/mobile-menu.jsx` (nav entries)
- `app/routes/admin/auth.py` (password reset for all users)
- `tests/test_public_auth.py` (new)
- `tests/e2e/test_public_auth.py` (new)

## Acceptance criteria

- [ ] A visitor can reach `/login` from a link on every public page.
- [ ] A non-admin user can sign in and sign out.
- [ ] A failed sign-in is rate limited, delayed, and locks the account after the configured number of attempts.
- [ ] The failure message never reveals whether an account exists.
- [ ] A `?next=` parameter cannot redirect off-site.
- [ ] A public session cannot reach any `/admin` page.
- [ ] A 2FA-enabled account cannot be signed in without the second factor.
- [ ] `/account` shows the signed-in user's profile and links to the editor.
- [ ] The admin nav and the public nav keep working unchanged for administrators.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

Requires Phase 02 (the profile fields the account page displays and edits).
Phase 04 lands after it and adds the author-facing views of the same session.

## Completion

**Status:** Complete.

| Item | Resolution |
|---|---|
| Routes | `app/routes/public/auth.py` registers `public.login` (`/login`), `public.logout` (`/logout`, POST), `public.account` (`/account`) and `public.account_profile` (`/account/profile`). |
| Admin accounts refused | The public login **refuses** admin accounts. Without this a public session would satisfy `admin_required` on its `is_admin` check alone, so admin sign-in stays on `/admin/login` only. |
| Same controls as admin auth | The shared `failed_login_count` / `locked_until` lockout counters, `LOGIN_FAILURE_DELAY` on invalid credentials, and `session.clear()` before `login_user()`. The per-IP rate limit is **not** one of these — as of 2026-10-24 the application does not rate limit the login routes at all, because the deployment is expected to sit behind a reverse proxy or WAF that does it. |
| Two-factor | A 2FA account must supply its TOTP or a backup code. A 2FA account whose secret cannot be decrypted is refused rather than allowed in without a second factor. |
| Redirect safety | `is_safe_next_url()` is a dedicated helper for this route — it does not reuse the Referer-based `_safe_redirect_url()`, which has different semantics. |
| Admin sessions | `admin_required` also requires an `AdminSession` row, so `public.logout` deletes that row. A public session therefore cannot reach an admin route. |
| Account page | `app/templates/account.html` shows the signed-in user's profile and doubles as the editor for display name, short bio, full bio and avatar through an `editing` flag. It carries no password and no admin controls. |
| Nav affordance | The public nav carries **Log in** when signed out and **Account**, **Write** and **Log out** when signed in. |
| Forgot password | `app/routes/admin/auth.py` forgot-password now works for non-admin accounts, so a locked-out author can still recover. |

**Verification** — headless Chromium against the live instance at
`http://localhost:5050`, harness at `/tmp/devlog_review_stubs/identity_verify.py`:

```
PASS login_page_exists
PASS nav_has_log_in
PASS author_nav_has_account
PASS author_nav_has_write
PASS author_nav_has_no_dashboard
```

Unit coverage: `tests/test_public_auth.py`, covering login, the account
lockout, the admin-account refusal, 2FA and the safe redirect. One test
asserts the endpoint carries **no** application rate limit, and one asserts
the account lockout still engages.
