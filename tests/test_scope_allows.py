import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"

from app.routes.api.auth import scope_allows, VALID_WILDCARD_SCOPES


class TestScopeAllows:
    def test_exact_match(self):
        assert scope_allows(["posts:read"], "posts:read") is True

    def test_exact_mismatch(self):
        assert scope_allows(["posts:write"], "posts:read") is False

    def test_admin_wildcard_grants_all(self):
        assert scope_allows(["admin:*"], "posts:read") is True
        assert scope_allows(["admin:*"], "posts:write") is True
        assert scope_allows(["admin:*"], "subscribers:read") is True
        assert scope_allows(["admin:*"], "subscribers:write") is True
        assert scope_allows(["admin:*"], "analytics:read") is True
        assert scope_allows(["admin:*"], "tags:read") is True
        assert scope_allows(["admin:*"], "pages:read") is True
        assert scope_allows(["admin:*"], "series:read") is True
        assert scope_allows(["admin:*"], "media:read") is True
        assert scope_allows(["admin:*"], "newsletter:send") is True

    def test_category_wildcard_grants_category(self):
        assert scope_allows(["posts:*"], "posts:read") is True
        assert scope_allows(["posts:*"], "posts:write") is True

    def test_category_wildcard_rejects_other_category(self):
        assert scope_allows(["posts:*"], "pages:read") is False
        assert scope_allows(["posts:*"], "subscribers:read") is False

    def test_invalid_category_wildcard_rejected(self):
        assert scope_allows(["post:*"], "posts:read") is False

    def test_empty_granted_scopes(self):
        assert scope_allows([], "posts:read") is False

    def test_empty_required_scope(self):
        assert scope_allows(["posts:read"], "") is False

    def test_unknown_granted_scope(self):
        assert scope_allows(["unknown:read"], "posts:read") is False

    def test_malformed_granted_scopes_denied(self):
        assert scope_allows(["not-a-scope"], "posts:read") is False

    def test_non_string_values_ignored(self):
        assert scope_allows([123, None, True, ["nested"]], "posts:read") is False

    def test_admin_wildcard_overrides_exact(self):
        assert scope_allows(["admin:*"], "anything:at-all") is True

    def test_multiple_scopes(self):
        assert scope_allows(["posts:read", "tags:read"], "posts:read") is True
        assert scope_allows(["posts:read", "tags:read"], "tags:read") is True
        assert scope_allows(["posts:read", "tags:read"], "pages:read") is False

    def test_category_wildcard_in_valid_set(self):
        for scope in VALID_WILDCARD_SCOPES:
            category = scope.split(":")[0]
            assert scope_allows([scope], f"{category}:read") is True

    def test_star_alone_not_valid(self):
        assert scope_allows(["*"], "posts:read") is False
