"""AES-256-GCM encryption for sensitive data at rest."""

from __future__ import annotations

import binascii
import base64
import os
import logging

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    AESGCM = None  # type: ignore[misc,assignment]  # noqa: F811

logger = logging.getLogger(__name__)

NONCE_SIZE = 12
KEY_SIZE = 32


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""

    pass


def get_encryption_key() -> bytes:
    """Get the encryption key from SECRET_KEY config.

    Raises:
        EncryptionError: If no key is configured.
    """
    from app.config import SECRET_KEY

    key_source = SECRET_KEY or ""

    if not key_source:
        raise EncryptionError("SECRET_KEY not configured. Set SECRET_KEY environment variable.")

    key = key_source.encode("utf-8")
    if len(key) < KEY_SIZE:
        raise EncryptionError(
            f"SECRET_KEY must be at least {KEY_SIZE} bytes ({KEY_SIZE * 8} bits) for AES-256. "
            f"Got {len(key)} bytes. Use a longer key or generate one with: python3 -c 'import secrets; print(secrets.token_hex(32))'"
        )
    return key[:KEY_SIZE]


def encrypt(plaintext: str) -> str:
    """Encrypt plaintext using AES-256-GCM.

    Args:
        plaintext: The text to encrypt.

    Returns:
        Base64-encoded string containing nonce + ciphertext + tag.

    Raises:
        EncryptionError: If encryption fails.
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise EncryptionError(
            "cryptography library is not available. Install with: pip install cryptography"
        )

    if not plaintext:
        return ""

    try:
        key = get_encryption_key()
        nonce = os.urandom(NONCE_SIZE)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

        combined = nonce + ciphertext
        return base64.b64encode(combined).decode("utf-8")
    except (ValueError, EncryptionError) as e:
        logger.error("Failed to encrypt data: %s", e)
        raise EncryptionError(f"Encryption failed: {e}") from e


def decrypt(encrypted: str) -> str:
    """Decrypt data encrypted with AES-256-GCM.

    Args:
        encrypted: Base64-encoded string containing nonce + ciphertext + tag.

    Returns:
        The decrypted plaintext.

    Raises:
        EncryptionError: If decryption fails.
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise EncryptionError(
            "cryptography library is not available. Install with: pip install cryptography"
        )

    if not encrypted:
        return ""

    try:
        key = get_encryption_key()
        combined = base64.b64decode(encrypted.encode("utf-8"))

        if len(combined) < NONCE_SIZE:
            raise EncryptionError("Encrypted data too short")

        nonce = combined[:NONCE_SIZE]
        ciphertext = combined[NONCE_SIZE:]

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except (ValueError, binascii.Error, EncryptionError) as e:
        logger.error("Failed to decrypt data: %s", e)
        raise EncryptionError(f"Decryption failed: {e}") from e
