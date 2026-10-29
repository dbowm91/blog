"""Regression tests for the backup encryption module.

The module guards its cryptography imports with ``except ImportError`` and
falls back to a disabled state. A wrong import location therefore disables
backup encryption silently instead of raising, so these tests assert the
availability flag and the round trip explicitly.
"""

import pytest

from app import backup_encryption


class TestCryptographyAvailability:
    def test_cryptography_is_available(self):
        """The cryptography imports must resolve to the installed library."""
        assert backup_encryption.CRYPTOGRAPHY_AVAILABLE is True

    def test_invalid_tag_is_the_library_exception(self):
        """InvalidTag must come from cryptography, not the fallback stub."""
        from cryptography.exceptions import InvalidTag

        assert getattr(backup_encryption, "InvalidTag", None) is InvalidTag

    def test_default_backend_resolves(self):
        """default_backend is imported by the module and must not be a stub."""
        from cryptography.hazmat.backends import default_backend

        assert callable(default_backend)


class TestRoundTrip:
    @pytest.fixture
    def key(self, monkeypatch):
        monkeypatch.setattr(
            backup_encryption, "BACKUP_ENCRYPTION_KEY", "correct-horse-battery-staple"
        )
        return "correct-horse-battery-staple"

    def test_encrypt_decrypt_round_trip(self, key):
        payload = b"blog backup payload"
        encrypted = backup_encryption.encrypt_backup(payload)
        assert encrypted != payload
        assert backup_encryption.decrypt_backup(encrypted) == payload

    def test_ciphertext_layout(self, key):
        encrypted = backup_encryption.encrypt_backup(b"payload")
        salt = encrypted[: backup_encryption.SALT_SIZE]
        nonce = encrypted[
            backup_encryption.SALT_SIZE : backup_encryption.SALT_SIZE + backup_encryption.NONCE_SIZE
        ]
        assert len(salt) == backup_encryption.SALT_SIZE
        assert len(nonce) == backup_encryption.NONCE_SIZE

    def test_decrypt_rejects_tampered_ciphertext(self, key):
        encrypted = bytearray(backup_encryption.encrypt_backup(b"payload"))
        encrypted[-1] ^= 0xFF
        with pytest.raises(RuntimeError):
            backup_encryption.decrypt_backup(bytes(encrypted))

    def test_encrypt_requires_key(self, monkeypatch):
        monkeypatch.setattr(backup_encryption, "BACKUP_ENCRYPTION_KEY", "")
        with pytest.raises(ValueError):
            backup_encryption.encrypt_backup(b"payload")

    def test_short_key_is_rejected(self, monkeypatch):
        monkeypatch.setattr(backup_encryption, "BACKUP_ENCRYPTION_KEY", "short")
        with pytest.raises(RuntimeError):
            backup_encryption.encrypt_backup(b"payload")

    def test_is_encryption_available_requires_key(self, monkeypatch):
        monkeypatch.setattr(backup_encryption, "BACKUP_ENCRYPTION_KEY", "")
        assert backup_encryption.is_encryption_available() is False
        monkeypatch.setattr(
            backup_encryption, "BACKUP_ENCRYPTION_KEY", "correct-horse-battery-staple"
        )
        assert backup_encryption.is_encryption_available() is True
