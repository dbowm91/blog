import pytest
from app.models import Series, Post, PostSeries
from app.utils import utc_now


def test_series_list_authenticated(authenticated_client, db):
    """Test series list page loads for authenticated admin."""
    response = authenticated_client.get("/admin/series")
    assert response.status_code == 200


def test_series_list_empty(authenticated_client, db):
    """Test series list with no series."""
    response = authenticated_client.get("/admin/series")
    assert response.status_code == 200
    assert b"No series found" in response.data or b"series" in response.data.lower()


def test_series_new_get(authenticated_client):
    """Test series new page loads."""
    response = authenticated_client.get("/admin/series/new")
    assert response.status_code == 200
    assert b"New Series" in response.data or b"name" in response.data.lower()


def test_series_new_post_valid(authenticated_client, db):
    """Test creating a valid series."""
    response = authenticated_client.post(
        "/admin/series/new",
        data={"name": "Test Series", "description": "A test series", "slug": "test-series"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Test Series" in response.data
    series = db.session.execute(
        db.select(Series).filter_by(slug="test-series")
    ).scalar_one_or_none()
    assert series is not None
    assert series.name == "Test Series"


def test_series_new_post_duplicate_slug(authenticated_client, db):
    """Test creating series with duplicate slug fails."""
    series = Series(name="Existing Series", slug="existing-series")
    db.session.add(series)
    db.session.commit()
    response = authenticated_client.post(
        "/admin/series/new",
        data={"name": "New Series", "slug": "existing-series"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"already exists" in response.data.lower()


def test_series_edit_get(authenticated_client, db):
    """Test series edit page loads."""
    series = Series(name="Edit Me", slug="edit-me")
    db.session.add(series)
    db.session.commit()
    response = authenticated_client.get(f"/admin/series/{series.id}/edit")
    assert response.status_code == 200
    assert b"Edit Me" in response.data


def test_series_edit_post_valid(authenticated_client, db):
    """Test editing a series."""
    series = Series(name="Old Name", slug="old-slug")
    db.session.add(series)
    db.session.commit()
    response = authenticated_client.post(
        f"/admin/series/{series.id}/edit",
        data={"name": "New Name", "slug": "new-slug", "description": "Updated"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"New Name" in response.data
    db.session.refresh(series)
    assert series.name == "New Name"
    assert series.slug == "new-slug"


def test_series_delete(authenticated_client, db):
    """Test deleting a series."""
    series = Series(name="Delete Me", slug="delete-me")
    db.session.add(series)
    db.session.commit()
    response = authenticated_client.post(
        f"/admin/series/{series.id}/delete",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"deleted successfully" in response.data.lower()
    deleted = db.session.execute(
        db.select(Series).filter_by(id=series.id)
    ).scalar_one_or_none()
    assert deleted is None


def test_series_posts_get(authenticated_client, db, sample_post):
    """Test series posts page loads."""
    series = Series(name="My Series", slug="my-series")
    db.session.add(series)
    db.session.commit()
    response = authenticated_client.get(f"/admin/series/{series.id}/posts")
    assert response.status_code == 200
    assert b"My Series" in response.data


def test_series_posts_add_post(authenticated_client, db, sample_post):
    """Test adding a post to a series."""
    series = Series(name="My Series", slug="my-series")
    db.session.add(series)
    db.session.commit()
    response = authenticated_client.post(
        f"/admin/series/{series.id}/posts",
        data={"action": "add", "post_id": sample_post.id},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"added to series" in response.data.lower()
    ps = db.session.execute(
        db.select(PostSeries).filter_by(series_id=series.id, post_id=sample_post.id)
    ).scalar_one_or_none()
    assert ps is not None


def test_series_posts_remove_post(authenticated_client, db, sample_post):
    """Test removing a post from a series."""
    series = Series(name="My Series", slug="my-series")
    db.session.add(series)
    db.session.commit()
    ps = PostSeries(series_id=series.id, post_id=sample_post.id, order_index=1)
    db.session.add(ps)
    db.session.commit()
    response = authenticated_client.post(
        f"/admin/series/{series.id}/posts",
        data={"action": "remove", "post_series_id": ps.id},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"removed from series" in response.data.lower()
    deleted = db.session.execute(
        db.select(PostSeries).filter_by(id=ps.id)
    ).scalar_one_or_none()
    assert deleted is None


def test_series_reorder(authenticated_client, db, sample_post):
    """Test reordering posts in a series via AJAX."""
    series = Series(name="My Series", slug="my-series")
    db.session.add(series)
    db.session.commit()
    ps = PostSeries(series_id=series.id, post_id=sample_post.id, order_index=1)
    db.session.add(ps)
    db.session.commit()
    response = authenticated_client.post(
        f"/admin/series/{series.id}/reorder",
        json={"order": [{"id": ps.id, "order": 2}]},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json["success"] is True
    db.session.refresh(ps)
    assert ps.order_index == 2
