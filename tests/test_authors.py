"""Tests for post authorship and author pages."""

import hashlib
import json
import os
import re

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")

import pytest
from sqlalchemy import select

from app.models import ApiToken, Post, User
from app.routes.public import public
from app.routes.public.authors import register_author_routes
from app.services.authors import resolve_author, resolve_author_id
from app.utils import utc_now

register_author_routes(public)

TEST_PASSWORD = os.environ["ADMIN_PASSWORD"]


@pytest.fixture()
def author_user(db):
    """A user with a profile that can author posts."""
    user = User(
        username="alice",
        email="alice@example.com",
        display_name="Alice Author",
        bio_short="Writes about testing.",
        bio_full="**Bold** introduction",
    )
    user.set_password(TEST_PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def scoped_token(db):
    """Factory for scoped API tokens."""

    def _create(scopes, raw="test-author-token"):
        token = ApiToken(
            name="author-test-token",
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            scopes=scopes,
        )
        db.session.add(token)
        db.session.commit()
        return raw

    return _create


def _json_ld(html):
    """Extract the JSON-LD payload of a rendered page."""
    match = re.search(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S)
    assert match is not None, "no JSON-LD block found"
    return json.loads(match.group(1))


def test_resolve_author_returns_the_assigned_user(db, admin_user):
    """A post with an author resolves that user."""
    post = Post(title="Authored", slug="authored", body="Body", author_id=admin_user.id)
    db.session.add(post)
    db.session.commit()

    view = resolve_author(post)

    assert view.name == admin_user.profile_name
    assert view.username == admin_user.username
    assert view.bio_short == admin_user.bio_short
    assert view.bio_full == admin_user.bio_full


def test_resolve_author_falls_back_to_the_config_author(db, admin_user, monkeypatch):
    """A post without an author falls back to the config author."""
    monkeypatch.setattr("app.services.authors.AUTHOR_NAME", "Config Author")
    monkeypatch.setattr("app.services.authors.AUTHOR_ROLE", "Editor")
    post = Post(title="Orphan", slug="orphan", body="Body")
    db.session.add(post)
    db.session.commit()

    view = resolve_author(post)

    assert view.name == "Config Author"
    assert view.role == "Editor"
    assert view.username is None


def test_resolve_author_falls_back_to_the_site_title(db, admin_user, monkeypatch):
    """A post without an author and without a config author uses the site title."""
    monkeypatch.setattr("app.services.authors.AUTHOR_NAME", "")
    monkeypatch.setattr("app.services.authors.APP_TITLE", "My Site")
    post = Post(title="Orphan", slug="orphan", body="Body")
    db.session.add(post)
    db.session.commit()

    view = resolve_author(post)

    assert view.name == "My Site"
    assert view.name != ""
    assert view.username is None


def test_author_page_shows_the_bio_and_the_published_posts(client, db, author_user):
    """The author page shows the bio and the published posts only."""
    published = Post(
        title="Published Post",
        slug="published-post",
        body="Body",
        summary="Published summary",
        published=True,
        published_at=utc_now(),
        author_id=author_user.id,
    )
    draft = Post(
        title="Unpublished Draft",
        slug="unpublished-draft",
        body="Body",
        published=False,
        author_id=author_user.id,
    )
    db.session.add_all([published, draft])
    db.session.commit()

    response = client.get("/author/alice")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Alice Author" in html
    assert "Writes about testing." in html
    assert "<strong>Bold</strong>" in html
    assert "Published Post" in html
    assert "Published summary" in html
    assert "Unpublished Draft" not in html


def test_author_page_without_posts(client, db, author_user):
    """An author without published posts still gets a page."""
    response = client.get("/author/alice")

    assert response.status_code == 200
    assert "No published posts yet." in response.get_data(as_text=True)


def test_author_page_inline_style_uses_the_csp_nonce(client, db, author_user):
    """The page style block carries the nonce of the CSP header."""
    response = client.get("/author/alice")

    csp = response.headers.get("Content-Security-Policy", "")
    nonce = re.search(r"nonce-([\w+/=~-]+)", csp)
    assert nonce is not None
    assert f'nonce="{nonce.group(1)}"' in response.get_data(as_text=True)


def test_author_page_of_unknown_username_returns_404(client, db):
    """An unknown author URL is a 404."""
    response = client.get("/author/nobody")

    assert response.status_code == 404


def test_author_page_sanitises_the_full_bio(client, db):
    """The full bio is rendered as markdown and never executes scripts."""
    user = User(
        username="mallory",
        email="mallory@example.com",
        display_name="Mallory",
        bio_full="<script>window.__authorXss = 1</script>\n\n**Bold**",
    )
    user.set_password(TEST_PASSWORD)
    db.session.add(user)
    db.session.commit()

    response = client.get("/author/mallory")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "__authorXss" not in html
    assert "<strong>Bold</strong>" in html


def test_post_page_links_the_author(client, db, author_user):
    """The post page links the author name to the author page."""
    post = Post(
        title="Linked Post",
        slug="linked-post",
        body="Body",
        published=True,
        published_at=utc_now(),
        author_id=author_user.id,
    )
    db.session.add(post)
    db.session.commit()

    response = client.get("/post/linked-post")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'href="/author/alice"' in html
    assert "Alice Author" in html


def test_post_page_does_not_link_the_config_fallback_author(client, db, admin_user, monkeypatch):
    """The config fallback author has no profile page, so the name is not a link."""
    monkeypatch.setattr("app.services.authors.AUTHOR_NAME", "Config Author")
    post = Post(
        title="Fallback Post",
        slug="fallback-post",
        body="Body",
        published=True,
        published_at=utc_now(),
    )
    db.session.add(post)
    db.session.commit()

    response = client.get("/post/fallback-post")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "/author/" not in html
    assert "Config Author" in html


def test_listing_links_the_author(client, db, author_user):
    """The listing links the author name to the author page."""
    post = Post(
        title="Listed Post",
        slug="listed-post",
        body="Body",
        published=True,
        published_at=utc_now(),
        author_id=author_user.id,
    )
    db.session.add(post)
    db.session.commit()

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'href="/author/alice"' in html


def test_post_jsonld_carries_the_author(client, db, author_user):
    """The JSON-LD names the author and links the author page."""
    post = Post(
        title="Schema Post",
        slug="schema-post",
        body="Body",
        published=True,
        published_at=utc_now(),
        author_id=author_user.id,
    )
    db.session.add(post)
    db.session.commit()

    response = client.get("/post/schema-post")

    data = _json_ld(response.get_data(as_text=True))
    assert data["author"]["name"] == "Alice Author"
    assert data["author"]["url"].endswith("/author/alice")


def test_post_jsonld_without_a_real_author_has_no_url(client, db, admin_user, monkeypatch):
    """The JSON-LD of an authorless post carries a name but no author URL."""
    monkeypatch.setattr("app.services.authors.AUTHOR_NAME", "Config Author")
    post = Post(
        title="Schema Fallback Post",
        slug="schema-fallback-post",
        body="Body",
        published=True,
        published_at=utc_now(),
    )
    db.session.add(post)
    db.session.commit()

    response = client.get("/post/schema-fallback-post")

    data = _json_ld(response.get_data(as_text=True))
    assert data["author"]["name"] == "Config Author"
    assert "url" not in data["author"]


def test_editor_renders_the_author_select(authenticated_client, db, author_user):
    """The editor offers the users that can author posts."""
    response = authenticated_client.get("/admin/new")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'name="author_id"' in html
    assert "Alice Author" in html


def test_non_admin_may_only_assign_themselves(db, admin_user, author_user):
    """A non-admin signed-in user may not assign a post to somebody else."""
    with pytest.raises(ValueError):
        resolve_author_id(str(admin_user.id), author_user)

    assert resolve_author_id(str(author_user.id), author_user) == author_user.id


def test_new_post_defaults_to_the_signed_in_author(authenticated_client, db, admin_user):
    """A post created without an author is authored by the signed-in user."""
    response = authenticated_client.post(
        "/admin/new",
        data={"title": "Defaults", "body": "Body"},
    )

    assert response.status_code == 302
    db.session.expire_all()
    post = db.session.execute(select(Post).filter_by(title="Defaults")).scalar_one()
    assert post.author_id == admin_user.id


def test_admin_may_assign_another_author(authenticated_client, db, admin_user, author_user):
    """An admin may assign any author."""
    response = authenticated_client.post(
        "/admin/new",
        data={"title": "Assigned", "body": "Body", "author_id": str(author_user.id)},
    )

    assert response.status_code == 302
    db.session.expire_all()
    post = db.session.execute(select(Post).filter_by(title="Assigned")).scalar_one()
    assert post.author_id == author_user.id


def test_api_exposes_the_author(client, db, author_user, scoped_token):
    """The API payload carries the author of a post."""
    post = Post(
        title="API Post",
        slug="api-post",
        body="Body",
        published=True,
        published_at=utc_now(),
        author_id=author_user.id,
    )
    db.session.add(post)
    db.session.commit()
    token = scoped_token(["posts:read"])

    response = client.get("/api/posts", headers={"X-API-Key": token})

    assert response.status_code == 200
    payload = response.get_json()["posts"][0]
    assert payload["author"]["username"] == "alice"
    assert payload["author"]["name"] == "Alice Author"
    assert payload["author"]["url"] == "/author/alice"


def test_api_sets_the_author_with_the_write_scope(client, db, author_user, scoped_token):
    """A token with posts:write may set the author of a post."""
    token = scoped_token(["posts:write"])

    response = client.post(
        "/api/posts",
        headers={"X-API-Key": token},
        json={"title": "With Author", "body": "Body", "author_id": author_user.id},
    )

    assert response.status_code == 201
    assert response.get_json()["author"]["username"] == "alice"


def test_api_refuses_to_set_the_author_without_the_scope(client, db, admin_user, scoped_token):
    """A token without posts:write may not set the author of a post."""
    token = scoped_token(["posts:read"])

    response = client.post(
        "/api/posts",
        headers={"X-API-Key": token},
        json={"title": "No Author", "body": "Body", "author_id": admin_user.id},
    )

    assert response.status_code == 403
    assert "scope" in response.get_json()["error"]


def test_sitemap_lists_author_pages(client, db, author_user):
    """The sitemap lists the pages of the authors with published posts."""
    post = Post(
        title="Sitemap Post",
        slug="sitemap-post",
        body="Body",
        published=True,
        published_at=utc_now(),
        author_id=author_user.id,
    )
    db.session.add(post)
    db.session.commit()

    response = client.get("/sitemap.xml")

    assert response.status_code == 200
    assert "/author/alice" in response.get_data(as_text=True)
