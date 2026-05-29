"""Tests for Tags, Pages, and Series API endpoints."""

import os

os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars-long-for-testing"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["API_KEY"] = "test-api-key-12345"
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"


class TestTagsAPI:
    """Tests for Tags API endpoints."""

    def test_list_tags_empty(self, client):
        """Test listing tags when none exist."""
        response = client.get("/api/tags", headers={"X-API-Key": "test-api-key-12345"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["tags"] == []
        assert data["total"] == 0

    def test_list_tags(self, client, db, admin_user):
        """Test listing tags with data."""
        from app.models import Tag

        tag = Tag(name="Python", slug="python")
        db.session.add(tag)
        db.session.commit()

        response = client.get("/api/tags", headers={"X-API-Key": "test-api-key-12345"})
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["tags"]) == 1
        assert data["tags"][0]["name"] == "Python"
        assert data["tags"][0]["slug"] == "python"

    def test_get_tag(self, client, db, admin_user):
        """Test getting a single tag."""
        from app.models import Tag

        tag = Tag(name="Python", slug="python")
        db.session.add(tag)
        db.session.commit()

        response = client.get(f"/api/tags/{tag.id}", headers={"X-API-Key": "test-api-key-12345"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Python"

    def test_get_tag_not_found(self, client):
        """Test getting a non-existent tag."""
        response = client.get("/api/tags/9999", headers={"X-API-Key": "test-api-key-12345"})
        assert response.status_code == 404

    def test_create_tag(self, client, db, admin_user):
        """Test creating a tag."""
        response = client.post(
            "/api/tags",
            headers={"X-API-Key": "test-api-key-12345"},
            json={"name": "NewTag"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "NewTag"
        assert data["slug"] == "newtag"

    def test_create_duplicate_tag_returns_existing(self, client, db, admin_user):
        """Test creating a duplicate tag returns existing."""
        from app.models import Tag

        existing = Tag(name="Existing", slug="existing")
        db.session.add(existing)
        db.session.commit()

        response = client.post(
            "/api/tags",
            headers={"X-API-Key": "test-api-key-12345"},
            json={"name": "Existing"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Existing"

    def test_update_tag(self, client, db, admin_user):
        """Test updating a tag."""
        from app.models import Tag

        tag = Tag(name="Original", slug="original")
        db.session.add(tag)
        db.session.commit()

        response = client.put(
            f"/api/tags/{tag.id}",
            headers={"X-API-Key": "test-api-key-12345"},
            json={"name": "Updated"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Updated"
        assert data["slug"] == "updated"

    def test_delete_tag(self, client, db, admin_user):
        """Test deleting a tag."""
        from app.models import Tag

        tag = Tag(name="ToDelete", slug="todelete")
        db.session.add(tag)
        db.session.commit()
        tag_id = tag.id

        response = client.delete(
            f"/api/tags/{tag_id}",
            headers={"X-API-Key": "test-api-key-12345"},
        )
        assert response.status_code == 200

        deleted = db.session.get(Tag, tag_id)
        assert deleted is None


class TestPagesAPI:
    """Tests for Pages API endpoints."""

    def test_list_pages_empty(self, client):
        """Test listing pages when none exist."""
        response = client.get("/api/pages", headers={"X-API-Key": "test-api-key-12345"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["pages"] == []
        assert data["total"] == 0

    def test_list_pages(self, client, db, admin_user):
        """Test listing pages with data."""
        from app.models import Page

        page = Page(title="Test Page", slug="test-page", body="Content", published=True)
        db.session.add(page)
        db.session.commit()

        response = client.get("/api/pages", headers={"X-API-Key": "test-api-key-12345"})
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["pages"]) == 1
        assert data["pages"][0]["title"] == "Test Page"

    def test_get_page(self, client, db, admin_user):
        """Test getting a single page."""
        from app.models import Page

        page = Page(title="Test Page", slug="test-page", body="Content", published=True)
        db.session.add(page)
        db.session.commit()

        response = client.get(f"/api/pages/{page.id}", headers={"X-API-Key": "test-api-key-12345"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Test Page"

    def test_get_page_not_found(self, client):
        """Test getting a non-existent page."""
        response = client.get("/api/pages/9999", headers={"X-API-Key": "test-api-key-12345"})
        assert response.status_code == 404

    def test_create_page(self, client, db, admin_user):
        """Test creating a page."""
        response = client.post(
            "/api/pages",
            headers={"X-API-Key": "test-api-key-12345"},
            json={
                "title": "New Page",
                "body": "# Page Content",
                "published": True,
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "New Page"
        assert data["body"] == "# Page Content"
        assert data["published"] is True

    def test_update_page(self, client, db, admin_user):
        """Test updating a page."""
        from app.models import Page

        page = Page(title="Original", slug="original", body="Content")
        db.session.add(page)
        db.session.commit()

        response = client.put(
            f"/api/pages/{page.id}",
            headers={"X-API-Key": "test-api-key-12345"},
            json={"title": "Updated", "body": "New content"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Updated"

    def test_delete_page(self, client, db, admin_user):
        """Test deleting a page."""
        from app.models import Page

        page = Page(title="ToDelete", slug="to-delete", body="Content")
        db.session.add(page)
        db.session.commit()
        page_id = page.id

        response = client.delete(
            f"/api/pages/{page_id}",
            headers={"X-API-Key": "test-api-key-12345"},
        )
        assert response.status_code == 200

        deleted = db.session.get(Page, page_id)
        assert deleted is None


class TestSeriesAPI:
    """Tests for Series API endpoints."""

    def test_list_series_empty(self, client):
        """Test listing series when none exist."""
        response = client.get("/api/series", headers={"X-API-Key": "test-api-key-12345"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["series"] == []
        assert data["total"] == 0

    def test_list_series(self, client, db, admin_user):
        """Test listing series with data."""
        from app.models import Series

        series = Series(name="Test Series", slug="test-series", description="A test series")
        db.session.add(series)
        db.session.commit()

        response = client.get("/api/series", headers={"X-API-Key": "test-api-key-12345"})
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["series"]) == 1
        assert data["series"][0]["name"] == "Test Series"

    def test_get_series(self, client, db, admin_user):
        """Test getting a single series."""
        from app.models import Series

        series = Series(name="Test Series", slug="test-series")
        db.session.add(series)
        db.session.commit()

        response = client.get(
            f"/api/series/{series.id}", headers={"X-API-Key": "test-api-key-12345"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Test Series"

    def test_get_series_not_found(self, client):
        """Test getting a non-existent series."""
        response = client.get("/api/series/9999", headers={"X-API-Key": "test-api-key-12345"})
        assert response.status_code == 404

    def test_create_series(self, client, db, admin_user):
        """Test creating a series."""
        response = client.post(
            "/api/series",
            headers={"X-API-Key": "test-api-key-12345"},
            json={
                "name": "New Series",
                "description": "A new series",
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "New Series"
        assert data["slug"] == "new-series"

    def test_update_series(self, client, db, admin_user):
        """Test updating a series."""
        from app.models import Series

        series = Series(name="Original", slug="original", description="Original desc")
        db.session.add(series)
        db.session.commit()

        response = client.put(
            f"/api/series/{series.id}",
            headers={"X-API-Key": "test-api-key-12345"},
            json={"name": "Updated", "description": "New desc"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Updated"

    def test_delete_series(self, client, db, admin_user):
        """Test deleting a series."""
        from app.models import Series

        series = Series(name="ToDelete", slug="to-delete")
        db.session.add(series)
        db.session.commit()
        series_id = series.id

        response = client.delete(
            f"/api/series/{series_id}",
            headers={"X-API-Key": "test-api-key-12345"},
        )
        assert response.status_code == 200

        deleted = db.session.get(Series, series_id)
        assert deleted is None

    def test_add_post_to_series(self, client, db, admin_user):
        """Test adding a post to a series."""
        from app.models import Series, Post

        series = Series(name="Test Series", slug="test-series")
        post = Post(title="Test Post", slug="test-post", body="Content", published=True)
        db.session.add(series)
        db.session.add(post)
        db.session.commit()

        response = client.post(
            f"/api/series/{series.id}/posts",
            headers={"X-API-Key": "test-api-key-12345"},
            json={"post_id": post.id},
        )
        assert response.status_code == 201

    def test_remove_post_from_series(self, client, db, admin_user):
        """Test removing a post from a series."""
        from app.models import Series, Post, PostSeries

        series = Series(name="Test Series", slug="test-series")
        post = Post(title="Test Post", slug="test-post", body="Content", published=True)
        db.session.add(series)
        db.session.add(post)
        db.session.flush()

        ps = PostSeries(series_id=series.id, post_id=post.id, order_index=1)
        db.session.add(ps)
        db.session.commit()

        response = client.delete(
            f"/api/series/{series.id}/posts/{post.id}",
            headers={"X-API-Key": "test-api-key-12345"},
        )
        assert response.status_code == 200


class TestScopedTokens:
    """Tests for scoped API tokens."""

    def test_missing_scope_returns_403(self, client, db, admin_user):
        """Test that missing scope returns 403."""
        from app.models import ApiToken
        import hashlib

        token = ApiToken(
            name="ReadOnly",
            token_hash=hashlib.sha256("test-token".encode()).hexdigest(),
            scopes=["posts:read"],
        )
        db.session.add(token)
        db.session.commit()

        response = client.post(
            "/api/posts",
            headers={"X-API-Key": "test-token"},
            json={"title": "Test", "body": "Content"},
        )
        assert response.status_code == 403
        data = response.get_json()
        assert "Missing scope" in data["error"]

    def test_legacy_key_has_all_scopes(self, client, db, admin_user):
        """Test that legacy API key has all scopes."""
        response = client.post(
            "/api/posts",
            headers={"X-API-Key": "test-api-key-12345"},
            json={"title": "Test Post", "body": "Content"},
        )
        assert response.status_code == 201
