"""Tests for backup_integrity module."""

import gzip
import hashlib
import sqlite3
import zlib
from pathlib import Path

import pytest


class TestCalculateChecksum:
    """Tests for calculate_checksum function."""

    def test_calculate_checksum_empty_file(self, tmp_path):
        """Test checksum of empty file."""
        from app.backup_integrity import calculate_checksum

        empty_file = tmp_path / "empty.db"
        empty_file.write_bytes(b"")

        result = calculate_checksum(empty_file)
        expected = hashlib.sha256(b"").hexdigest()
        assert result == expected

    def test_calculate_checksum_small_file(self, tmp_path):
        """Test checksum of small file."""
        from app.backup_integrity import calculate_checksum

        small_file = tmp_path / "small.db"
        small_file.write_bytes(b"SELECT * FROM posts;")

        result = calculate_checksum(small_file)
        expected = hashlib.sha256(b"SELECT * FROM posts;").hexdigest()
        assert result == expected

    def test_calculate_checksum_large_file(self, tmp_path):
        """Test checksum of large file (multiple chunks)."""
        from app.backup_integrity import calculate_checksum

        large_data = b"x" * 20000
        large_file = tmp_path / "large.db"
        large_file.write_bytes(large_data)

        result = calculate_checksum(large_file)
        expected = hashlib.sha256(large_data).hexdigest()
        assert result == expected

    def test_calculate_checksum_nonexistent_file(self, tmp_path):
        """Test checksum of nonexistent file raises error."""
        from app.backup_integrity import calculate_checksum

        nonexistent = tmp_path / "does_not_exist.db"
        with pytest.raises(FileNotFoundError):
            calculate_checksum(nonexistent)


class TestVerifyBackupIntegrity:
    """Tests for verify_backup_integrity function."""

    def create_valid_sqlite_db(self, path: Path) -> None:
        """Create a valid SQLite database file."""
        conn = sqlite3.connect(str(path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test (name) VALUES ('hello')")
        conn.commit()
        conn.close()

    def test_verify_backup_integrity_valid_db(self, tmp_path):
        """Test verification of valid SQLite database."""
        from app.backup_integrity import verify_backup_integrity

        db_path = tmp_path / "valid.db"
        self.create_valid_sqlite_db(db_path)

        is_valid, message = verify_backup_integrity(db_path)
        assert is_valid is True
        assert "valid" in message.lower()

    def test_verify_backup_integrity_nonexistent(self, tmp_path):
        """Test verification of nonexistent file."""
        from app.backup_integrity import verify_backup_integrity

        nonexistent = tmp_path / "does_not_exist.db"
        is_valid, message = verify_backup_integrity(nonexistent)
        assert is_valid is False
        assert "not found" in message.lower()

    def test_verify_backup_integrity_empty_file(self, tmp_path):
        """Test verification of empty file."""
        from app.backup_integrity import verify_backup_integrity

        empty_file = tmp_path / "empty.db"
        empty_file.write_bytes(b"")

        is_valid, message = verify_backup_integrity(empty_file)
        assert is_valid is False
        assert "empty" in message.lower()

    def test_verify_backup_integrity_invalid_header(self, tmp_path):
        """Test verification of file with invalid SQLite header."""
        from app.backup_integrity import verify_backup_integrity

        invalid_file = tmp_path / "invalid.db"
        invalid_file.write_bytes(b"not a sqlite database")

        is_valid, message = verify_backup_integrity(invalid_file)
        assert is_valid is False
        assert "invalid" in message.lower() or "sqlite" in message.lower()

    def test_verify_backup_integrity_corrupted_db(self, tmp_path):
        """Test verification of corrupted SQLite database."""
        from app.backup_integrity import verify_backup_integrity

        corrupted_file = tmp_path / "corrupted.db"
        corrupted_file.write_bytes(b"SQLite format 3 corrupted content")

        is_valid, message = verify_backup_integrity(corrupted_file)
        assert is_valid is False

    def test_verify_backup_integrity_gzipped(self, tmp_path):
        """Test verification of gzipped SQLite database."""
        from app.backup_integrity import verify_backup_integrity

        db_path = tmp_path / "original.db"
        self.create_valid_sqlite_db(db_path)

        gz_path = tmp_path / "backup.db.gz"
        with open(db_path, "rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                f_out.write(f_in.read())

        is_valid, message = verify_backup_integrity(gz_path)
        assert is_valid is True

    def test_verify_backup_integrity_no_tables(self, tmp_path):
        """Test verification of valid SQLite with no tables."""
        from app.backup_integrity import verify_backup_integrity

        empty_db = tmp_path / "empty.db"
        conn = sqlite3.connect(str(empty_db))
        conn.execute("CREATE TABLE dummy (id INTEGER)")  # Create table, then drop it
        conn.execute("DROP TABLE dummy")
        conn.execute("VACUUM")  # Compact the database
        conn.close()

        # Re-open and verify it passes integrity but has no tables
        is_valid, message = verify_backup_integrity(empty_db)
        assert is_valid is False
        assert "no tables" in message.lower()


class TestVerifyBackupSet:
    """Tests for verify_backup_set function."""

    def create_valid_sqlite_db(self, path: Path) -> None:
        """Create a valid SQLite database file."""
        conn = sqlite3.connect(str(path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

    def test_verify_backup_set_empty_directory(self, tmp_path):
        """Test verification of empty backup directory."""
        from app.backup_integrity import verify_backup_set

        empty_dir = tmp_path / "empty_backups"
        empty_dir.mkdir()

        results = verify_backup_set(empty_dir)
        assert results["total"] == 0
        assert results["valid"] == 0
        assert results["invalid"] == 0

    def test_verify_backup_set_nonexistent_directory(self, tmp_path):
        """Test verification of nonexistent directory."""
        from app.backup_integrity import verify_backup_set

        nonexistent = tmp_path / "does_not_exist"

        results = verify_backup_set(nonexistent)
        assert "error" in results

    def test_verify_backup_set_multiple_backups(self, tmp_path):
        """Test verification of multiple backup files."""
        from app.backup_integrity import verify_backup_set

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        for i in range(3):
            db_path = backup_dir / f"blog_backup_{i}.db"
            self.create_valid_sqlite_db(db_path)

        results = verify_backup_set(backup_dir)
        assert results["total"] == 3
        assert results["valid"] == 3
        assert results["invalid"] == 0

    def test_verify_backup_set_expected_count_warning(self, tmp_path):
        """Test verification shows warning when fewer backups than expected."""
        from app.backup_integrity import verify_backup_set

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        db_path = backup_dir / "blog_backup_0.db"
        self.create_valid_sqlite_db(db_path)

        results = verify_backup_set(backup_dir, expected_count=5)
        assert results["total"] == 1
        assert "warning" in results

    def test_verify_backup_set_mixed_valid_invalid(self, tmp_path):
        """Test verification of mix of valid and invalid backups."""
        from app.backup_integrity import verify_backup_set

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        valid_db = backup_dir / "blog_backup_0.db"
        self.create_valid_sqlite_db(valid_db)

        invalid_db = backup_dir / "blog_backup_1.db"
        invalid_db.write_bytes(b"not sqlite")

        results = verify_backup_set(backup_dir)
        assert results["total"] == 2
        assert results["valid"] == 1
        assert results["invalid"] == 1

    def test_verify_backup_set_ignores_non_backup_files(self, tmp_path):
        """Test that non-backup files are ignored."""
        from app.backup_integrity import verify_backup_set

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        db_path = backup_dir / "blog_backup_0.db"
        self.create_valid_sqlite_db(db_path)

        other_file = backup_dir / "readme.txt"
        other_file.write_text("Not a backup")

        results = verify_backup_set(backup_dir)
        assert results["total"] == 1


class TestCalculateBackupCrc:
    """Tests for calculate_backup_crc function."""

    def test_calculate_backup_crc_uncompressed(self, tmp_path):
        """Test CRC calculation for uncompressed file."""
        from app.backup_integrity import calculate_backup_crc

        file_path = tmp_path / "data.db"
        file_path.write_bytes(b"hello world")

        result = calculate_backup_crc(file_path)
        expected = hex(zlib.crc32(b"hello world") & 0xFFFFFFFF)
        assert result == expected

    def test_calculate_backup_crc_gzipped(self, tmp_path):
        """Test CRC calculation for gzipped file."""
        from app.backup_integrity import calculate_backup_crc
        import zlib

        file_path = tmp_path / "data.db"
        file_path.write_bytes(b"hello world")

        gz_path = tmp_path / "data.db.gz"
        with gzip.open(gz_path, "wb") as f:
            f.write(b"hello world")

        result = calculate_backup_crc(gz_path)
        expected = hex(zlib.crc32(b"hello world") & 0xFFFFFFFF)
        assert result == expected

    def test_calculate_backup_crc_empty_file(self, tmp_path):
        """Test CRC calculation for empty file."""
        from app.backup_integrity import calculate_backup_crc

        empty_file = tmp_path / "empty.db"
        empty_file.write_bytes(b"")

        result = calculate_backup_crc(empty_file)
        expected = hex(zlib.crc32(b"") & 0xFFFFFFFF)
        assert result == expected


class TestDetectBackupCorruption:
    """Tests for detect_backup_corruption function."""

    def create_valid_sqlite_db(self, path: Path) -> None:
        """Create a valid SQLite database file."""
        conn = sqlite3.connect(str(path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

    def test_detect_backup_corruption_nonexistent(self, tmp_path):
        """Test corruption detection for nonexistent file."""
        from app.backup_integrity import detect_backup_corruption

        nonexistent = tmp_path / "does_not_exist.db"
        is_corrupted, reason = detect_backup_corruption(nonexistent)
        assert is_corrupted is True
        assert "not exist" in reason.lower()

    def test_detect_backup_corruption_too_small(self, tmp_path):
        """Test corruption detection for file that is too small."""
        from app.backup_integrity import detect_backup_corruption

        small_file = tmp_path / "tiny.db"
        small_file.write_bytes(b"x" * 100)

        is_corrupted, reason = detect_backup_corruption(small_file)
        assert is_corrupted is True
        assert "too small" in reason.lower()

    def test_detect_backup_corruption_too_large(self, tmp_path):
        """Test corruption detection for file that is suspiciously large."""
        from app.backup_integrity import detect_backup_corruption

        large_file = tmp_path / "huge.db"
        large_file.write_bytes(b"x" * (11 * 1024 * 1024 * 1024))

        is_corrupted, reason = detect_backup_corruption(large_file)
        assert is_corrupted is True
        assert "large" in reason.lower()

    def test_detect_backup_corruption_valid_db(self, tmp_path):
        """Test corruption detection for valid database."""
        from app.backup_integrity import detect_backup_corruption

        db_path = tmp_path / "valid.db"
        self.create_valid_sqlite_db(db_path)

        is_corrupted, reason = detect_backup_corruption(db_path)
        assert is_corrupted is False
        assert "no corruption" in reason.lower()

    def test_detect_backup_corruption_invalid_header(self, tmp_path):
        """Test corruption detection for file with invalid header."""
        from app.backup_integrity import detect_backup_corruption

        invalid_file = tmp_path / "invalid.db"
        invalid_file.write_bytes(b"not sqlite" + b"x" * 500)

        is_corrupted, reason = detect_backup_corruption(invalid_file)
        assert is_corrupted is True
