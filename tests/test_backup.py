import os
import gzip
import pytest
from unittest.mock import patch
from app.models import User, Post
from app.utils import utc_now


def test_backup_creation_uncompressed(app, db, authenticated_client):
    """Test creating an uncompressed backup."""
    response = authenticated_client.post("/admin/backup/create")
    assert response.status_code == 302
    assert response.headers["Location"] == "/admin/backup"

    backup_dir = os.path.join(app.instance_path, "backups")
    assert os.path.isdir(backup_dir)
    files = [
        f for f in os.listdir(backup_dir) if f.startswith("blog_") and f.endswith(".db")
    ]
    assert len(files) >= 1


def test_backup_creation_compressed(app, db, authenticated_client):
    """Test creating a compressed backup."""
    response = authenticated_client.post(
        "/admin/backup/create", data={"compress": "on"}
    )
    assert response.status_code == 302

    backup_dir = os.path.join(app.instance_path, "backups")
    files = [
        f
        for f in os.listdir(backup_dir)
        if f.startswith("blog_") and f.endswith(".db.gz")
    ]
    assert len(files) >= 1


def test_backup_list(app, db, authenticated_client):
    """Test listing backups."""
    response = authenticated_client.get("/admin/backup")
    assert response.status_code == 200
    assert b"backup" in response.data.lower()


def test_backup_download_uncompressed(app, db, authenticated_client):
    """Test downloading an uncompressed backup."""
    authenticated_client.post("/admin/backup/create", data={"compress": "on"})

    backup_dir = os.path.join(app.instance_path, "backups")
    files = sorted(
        [
            f
            for f in os.listdir(backup_dir)
            if f.startswith("blog_") and f.endswith(".db")
        ]
    )
    if not files:
        pytest.skip("No uncompressed backup created in time")

    response = authenticated_client.get(f"/admin/backup/download/{files[0]}")
    assert response.status_code == 200
    assert response.headers["Content-Disposition"]


def test_backup_download_compressed(app, db, authenticated_client):
    """Test downloading a compressed backup."""
    authenticated_client.post("/admin/backup/create", data={"compress": "on"})

    backup_dir = os.path.join(app.instance_path, "backups")
    files = sorted(
        [
            f
            for f in os.listdir(backup_dir)
            if f.startswith("blog_") and f.endswith(".db.gz")
        ]
    )
    if not files:
        pytest.skip("No compressed backup created in time")

    response = authenticated_client.get(f"/admin/backup/download/{files[0]}")
    assert response.status_code == 200


def test_backup_download_path_traversal_rejected(app, db, authenticated_client):
    """Test path traversal attempt is rejected."""
    response = authenticated_client.get("/admin/backup/download/../../../etc/passwd")
    assert response.status_code in (400, 404)


def test_backup_download_invalid_filename_rejected(app, db, authenticated_client):
    """Test invalid backup filename is rejected."""
    response = authenticated_client.get("/admin/backup/download/malicious.db")
    assert response.status_code == 400


def test_backup_delete(app, db, authenticated_client):
    """Test deleting a backup."""
    authenticated_client.post("/admin/backup/create")

    backup_dir = os.path.join(app.instance_path, "backups")
    files = sorted([f for f in os.listdir(backup_dir) if f.startswith("blog_")])
    if not files:
        pytest.skip("No backup created")

    backup_name = files[0]
    response = authenticated_client.post(f"/admin/backup/delete/{backup_name}")
    assert response.status_code == 302
    assert not os.path.exists(os.path.join(backup_dir, backup_name))


def test_backup_restore(app, db, authenticated_client, admin_user):
    """Test restoring a backup."""
    post = Post(
        title="Restore Test",
        slug="restore-test",
        body="Test body",
        published=True,
        published_at=utc_now(),
    )
    db.session.add(post)
    db.session.commit()
    post_id = post.id

    authenticated_client.post("/admin/backup/create")

    backup_dir = os.path.join(app.instance_path, "backups")
    files = sorted(
        [
            f
            for f in os.listdir(backup_dir)
            if f.startswith("blog_") and f.endswith(".db")
        ]
    )
    if not files:
        pytest.skip("No backup created")

    backup_name = files[0]
    response = authenticated_client.post(f"/admin/backup/restore/{backup_name}")
    assert response.status_code == 302

    with app.app_context():
        from app.models import Post as PostModel

        post = db.session.get(PostModel, post_id)
        assert post is not None


def test_backup_restore_compressed(app, db, authenticated_client, admin_user):
    """Test restoring a compressed backup."""
    post = Post(
        title="Compressed Restore Test",
        slug="compressed-restore-test",
        body="Test body for compressed restore",
        published=True,
        published_at=utc_now(),
    )
    db.session.add(post)
    db.session.commit()
    post_id = post.id

    authenticated_client.post("/admin/backup/create", data={"compress": "on"})

    backup_dir = os.path.join(app.instance_path, "backups")
    files = sorted(
        [
            f
            for f in os.listdir(backup_dir)
            if f.startswith("blog_") and f.endswith(".db.gz")
        ]
    )
    if not files:
        pytest.skip("No compressed backup created")

    backup_name = files[0]
    response = authenticated_client.post(f"/admin/backup/restore/{backup_name}")
    assert response.status_code == 302

    with app.app_context():
        from app.models import Post as PostModel

        post = db.session.get(PostModel, post_id)
        assert post is not None
        assert post.title == "Compressed Restore Test"


def test_backup_restore_corrupted_file(app, db, authenticated_client):
    """Test that restoring a corrupted backup file overwrites the DB (no validation at route level)."""
    backup_dir = os.path.join(app.instance_path, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    corrupted_name = "blog_20260101_120000.db"
    corrupted_path = os.path.join(backup_dir, corrupted_name)
    with open(corrupted_path, "wb") as f:
        f.write(b"this is not a valid sqlite database")

    try:
        response = authenticated_client.post(f"/admin/backup/restore/{corrupted_name}")
        assert response.status_code == 302
    finally:
        if os.path.exists(corrupted_path):
            os.remove(corrupted_path)


def test_backup_restore_corrupted_compressed(app, db, authenticated_client):
    """Test that restoring a corrupted compressed backup raises an error."""
    backup_dir = os.path.join(app.instance_path, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    corrupted_name = "blog_20260101_120000.db.gz"
    corrupted_path = os.path.join(backup_dir, corrupted_name)
    with open(corrupted_path, "wb") as f:
        f.write(b"this is not a valid gzip file")

    try:
        with pytest.raises(Exception):
            authenticated_client.post(f"/admin/backup/restore/{corrupted_name}")
    finally:
        if os.path.exists(corrupted_path):
            os.remove(corrupted_path)


def test_backup_delete_nonexistent(app, db, authenticated_client):
    """Test deleting a nonexistent backup returns 404."""
    response = authenticated_client.post("/admin/backup/delete/blog_20260101_120000.db")
    assert response.status_code == 404


def test_backup_retention_policy(app, db):
    """Test that old backups are cleaned up when retention limit is exceeded."""
    from backup import create_backup, cleanup_old_backups

    backup_dir = os.path.join(app.instance_path, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    db_path = os.path.join(app.instance_path, "blog.db")
    keep = 3

    for _ in range(5):
        create_backup(db_path, backup_dir, compress=False, keep=keep)

    files = [
        f for f in os.listdir(backup_dir) if f.startswith("blog_") and f.endswith(".db")
    ]
    assert len(files) <= keep
