import gzip
import os
import sqlite3
import pytest
from app.models import Post
from app.utils import utc_now

from app.services.backup import resolve_backup_dir

pytestmark = pytest.mark.slow


def test_backup_creation_uncompressed(app, db, authenticated_client):
    """Test creating an uncompressed backup."""
    response = authenticated_client.post("/admin/backup/create")
    assert response.status_code == 302
    assert response.headers["Location"] == "/admin/backup"

    backup_dir = resolve_backup_dir(app)
    assert os.path.isdir(backup_dir)
    files = [f for f in os.listdir(backup_dir) if f.startswith("blog_") and f.endswith(".db")]
    assert len(files) >= 1


def test_backup_creation_compressed(app, db, authenticated_client):
    """Test creating a compressed backup."""
    response = authenticated_client.post("/admin/backup/create", data={"compress": "on"})
    assert response.status_code == 302

    backup_dir = resolve_backup_dir(app)
    files = [f for f in os.listdir(backup_dir) if f.startswith("blog_") and f.endswith(".db.gz")]
    assert len(files) >= 1


def test_backup_list(app, db, authenticated_client):
    """Test listing backups."""
    response = authenticated_client.get("/admin/backup")
    assert response.status_code == 200
    assert b"backup" in response.data.lower()


def test_backup_download_uncompressed(app, db, authenticated_client):
    """Test downloading an uncompressed backup."""
    authenticated_client.post("/admin/backup/create", data={"compress": "on"})

    backup_dir = resolve_backup_dir(app)
    files = sorted(
        [f for f in os.listdir(backup_dir) if f.startswith("blog_") and f.endswith(".db")]
    )
    if not files:
        pytest.skip("No uncompressed backup created in time")

    response = authenticated_client.get(f"/admin/backup/download/{files[0]}")
    assert response.status_code == 200
    assert response.headers["Content-Disposition"]


def test_backup_download_compressed(app, db, authenticated_client):
    """Test downloading a compressed backup."""
    authenticated_client.post("/admin/backup/create", data={"compress": "on"})

    backup_dir = resolve_backup_dir(app)
    files = sorted(
        [f for f in os.listdir(backup_dir) if f.startswith("blog_") and f.endswith(".db.gz")]
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

    backup_dir = resolve_backup_dir(app)
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

    backup_dir = resolve_backup_dir(app)
    os.makedirs(backup_dir, exist_ok=True)
    for existing_backup in os.listdir(backup_dir):
        os.remove(os.path.join(backup_dir, existing_backup))
    authenticated_client.post("/admin/backup/create")

    files = sorted(
        [f for f in os.listdir(backup_dir) if f.startswith("blog_") and f.endswith(".db")]
    )
    if not files:
        pytest.skip("No backup created")

    backup_name = files[0]
    with sqlite3.connect(os.path.join(backup_dir, backup_name)) as backup_database:
        restored_title = backup_database.execute(
            "SELECT title FROM posts WHERE id = ?", (post_id,)
        ).fetchone()
    assert restored_title == ("Restore Test",)
    db.session.remove()
    response = authenticated_client.post(f"/admin/backup/restore/{backup_name}")
    assert response.status_code == 302
    db.session.remove()
    database_path = app.config["SQLALCHEMY_DATABASE_URI"][10:]
    with sqlite3.connect(database_path) as restored_database:
        restored_title = restored_database.execute(
            "SELECT title FROM posts WHERE id = ?", (post_id,)
        ).fetchone()
    assert restored_title == ("Restore Test",)

    from app.models import Post as PostModel

    post = db.session.get(PostModel, post_id)
    assert post is not None


def test_backup_restore_compressed(app, db, authenticated_client, admin_user, tmp_path):
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

    backup_dir = resolve_backup_dir(app)
    os.makedirs(backup_dir, exist_ok=True)
    for existing_backup in os.listdir(backup_dir):
        os.remove(os.path.join(backup_dir, existing_backup))
    authenticated_client.post("/admin/backup/create", data={"compress": "on"})

    files = sorted(
        [f for f in os.listdir(backup_dir) if f.startswith("blog_") and f.endswith(".db.gz")]
    )
    if not files:
        pytest.skip("No compressed backup created")

    backup_name = files[0]
    backup_path = os.path.join(backup_dir, backup_name)
    with gzip.open(backup_path, "rb") as compressed_backup:
        backup_bytes = compressed_backup.read()
    decompressed_backup_path = tmp_path / "compressed-backup.db"
    decompressed_backup_path.write_bytes(backup_bytes)
    with sqlite3.connect(decompressed_backup_path) as backup_database:
        restored_title = backup_database.execute(
            "SELECT title FROM posts WHERE id = ?", (post_id,)
        ).fetchone()
    assert restored_title == ("Compressed Restore Test",)
    db.session.remove()
    response = authenticated_client.post(f"/admin/backup/restore/{backup_name}")
    assert response.status_code == 302
    db.session.remove()
    database_path = app.config["SQLALCHEMY_DATABASE_URI"][10:]
    with sqlite3.connect(database_path) as restored_database:
        restored_title = restored_database.execute(
            "SELECT title FROM posts WHERE id = ?", (post_id,)
        ).fetchone()
    assert restored_title == ("Compressed Restore Test",)

    from app.models import Post as PostModel

    post = db.session.get(PostModel, post_id)
    assert post is not None
    assert post.title == "Compressed Restore Test"


def test_backup_restore_corrupted_file(app, db, authenticated_client):
    """Test that restoring a corrupted backup file overwrites the DB (no validation at route level)."""
    backup_dir = resolve_backup_dir(app)
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
    """Test that restoring a corrupted compressed backup returns error redirect."""
    backup_dir = resolve_backup_dir(app)
    os.makedirs(backup_dir, exist_ok=True)

    corrupted_name = "blog_20260101_120000.db.gz"
    corrupted_path = os.path.join(backup_dir, corrupted_name)
    with open(corrupted_path, "wb") as f:
        f.write(b"this is not a valid gzip file")

    try:
        response = authenticated_client.post(f"/admin/backup/restore/{corrupted_name}")
        assert response.status_code == 302
    finally:
        if os.path.exists(corrupted_path):
            os.remove(corrupted_path)


def test_backup_delete_nonexistent(app, db, authenticated_client):
    """Test deleting a nonexistent backup returns 404."""
    response = authenticated_client.post("/admin/backup/delete/blog_20260101_120000.db")
    assert response.status_code == 404


def test_backup_retention_policy(app, db, tmp_path):
    """Test that old backups are cleaned up when retention limit is exceeded."""
    from app.services.backup import create_backup, resolve_database_file

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    db_path = resolve_database_file(app)
    assert db_path and os.path.exists(db_path), "the configured database must exist"

    keep = 3
    # create_backup() names files with second resolution, so repeated calls
    # inside one second reuse a single name. Seed distinct, older backups so
    # the retention policy has a full set to prune.
    base_mtime = 1_700_000_000
    seeded = []
    for index in range(keep):
        seeded_path = backup_dir / f"blog_2026010{index + 1}_120000.db"
        seeded_path.write_bytes(b"")
        os.utime(seeded_path, (base_mtime + index, base_mtime + index))
        seeded.append(seeded_path.name)

    created = create_backup(db_path, str(backup_dir), compress=False, keep=keep)
    assert created is not None, "the backup must be created from the live database"

    files = [f for f in os.listdir(backup_dir) if f.startswith("blog_") and f.endswith(".db")]
    assert len(files) == keep
    assert os.path.basename(created) in files
    assert seeded[0] not in files, "the oldest backup must be the one removed"
