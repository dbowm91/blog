from unittest.mock import patch, MagicMock
import os
import tempfile

from app.storage import (
    LocalStorageBackend,
    get_storage,
    storage_delete_file,
)


def test_local_storage_save_and_load():
    """Test LocalStorageBackend save and load."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalStorageBackend(tmpdir)
        # Save file
        result = backend.save("test.txt", b"hello")
        assert result == "test.txt"
        assert os.path.exists(os.path.join(tmpdir, "test.txt"))
        # Load file
        data = backend.load("test.txt")
        assert data == b"hello"
        # Load non-existent file
        data = backend.load("nonexistent.txt")
        assert data is None


def test_local_storage_delete():
    """Test LocalStorageBackend delete."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalStorageBackend(tmpdir)
        # Create file
        filepath = os.path.join(tmpdir, "test.txt")
        with open(filepath, "wb") as f:
            f.write(b"hello")
        # Delete
        result = backend.delete("test.txt")
        assert result is True
        assert not os.path.exists(filepath)
        # Delete non-existent
        result = backend.delete("nonexistent.txt")
        assert result is False


def test_local_storage_exists():
    """Test LocalStorageBackend exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalStorageBackend(tmpdir)
        # Create file
        filepath = os.path.join(tmpdir, "test.txt")
        with open(filepath, "wb") as f:
            f.write(b"hello")
        assert backend.exists("test.txt") is True
        assert backend.exists("nonexistent.txt") is False


def test_local_storage_url():
    """Test LocalStorageBackend url."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalStorageBackend(tmpdir)
        url = backend.url("test.txt")
        assert url == "/static/uploads/test.txt"


def test_local_storage_list_files():
    """Test LocalStorageBackend list_files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalStorageBackend(tmpdir)
        # Create files
        for i in range(3):
            with open(os.path.join(tmpdir, f"file{i}.txt"), "w") as f:
                f.write("test")
        files = backend.list_files()
        assert len(files) == 3
        assert "file1.txt" in files


def test_get_storage_local():
    """Test get_storage returns local backend by default."""
    with patch("app.storage.STORAGE_BACKEND", "local"):
        # Patch the default upload folder
        with patch("app.storage.os.path.join", return_value="/tmp/uploads"):
            storage = get_storage()
            assert isinstance(storage, LocalStorageBackend)


def test_storage_delete_file():
    """Test storage_delete_file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create file
        filepath = os.path.join(tmpdir, "test.txt")
        with open(filepath, "wb") as f:
            f.write(b"hello")
        with patch("app.storage.get_storage") as mock_get:
            mock_backend = MagicMock()
            mock_backend.delete.return_value = True
            mock_get.return_value = mock_backend
            result = storage_delete_file("test.txt")
            assert result is True
            mock_backend.delete.assert_called_once_with("test.txt")


def test_upload_with_processing_local():
    """Test upload_with_processing for local storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import app.storage as storage_module

        original_storage = storage_module._storage
        storage_module._storage = None
        with patch.dict(os.environ, {"UPLOAD_FOLDER": tmpdir}):
            storage_module._storage = None
            result, error = storage_module.upload_with_processing(
                "test.txt", b"hello", generate_variants=False
            )
            assert result == "test.txt"
            assert error is None
            assert os.path.exists(os.path.join(tmpdir, "test.txt"))
        storage_module._storage = original_storage
