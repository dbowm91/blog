"""AES-256-GCM encryption for webhook secrets at rest."""

import binascii
import base64
import os
import logging
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

NONCE_SIZE = 12
KEY_SIZE = 32


class WebhookEncryptionError(Exception):
    """Raised when encryption or decryption fails."""
    pass


def _get_encryption_key() -> bytes:
    """Get the encryption key from config or environment.

    The key can be provided as:
    - A hex-encoded string (64 characters) which will be decoded to 32 bytes
    - A raw string that is exactly 32 bytes

    Raises:
        WebhookEncryptionError: If no key is configured or key is invalid.
    """
    import binascii
    from app.config import WEBHOOK_ENCRYPTION_KEY

    key_source = WEBHOOK_ENCRYPTION_KEY or ""

    if not key_source:
        raise WebhookEncryptionError(
            "WEBHOOK_ENCRYPTION_KEY not configured. "
            "Set WEBHOOK_ENCRYPTION_KEY environment variable."
        )

    key = key_source.encode("utf-8")

    if len(key) == 64:
        try:
            return binascii.unhexlify(key)
        except (binascii.Error, ValueError) as e:
            raise WebhookEncryptionError(
                f"WEBHOOK_ENCRYPTION_KEY is not valid hex: {e}"
            )

    if len(key) != KEY_SIZE:
        raise WebhookEncryptionError(
            f"WEBHOOK_ENCRYPTION_KEY must be {KEY_SIZE} bytes or 64 hex characters"
        )
    return key


def encrypt_webhook_secret(plaintext: str) -> str:
    """Encrypt a webhook secret using AES-256-GCM.

    Args:
        plaintext: The webhook secret to encrypt.

    Returns:
        Base64-encoded string containing nonce + ciphertext + tag.

    Raises:
        WebhookEncryptionError: If encryption fails.
    """
    if not plaintext:
        return ""

    try:
        key = _get_encryption_key()
        nonce = os.urandom(NONCE_SIZE)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

        combined = nonce + ciphertext
        return base64.b64encode(combined).decode("utf-8")
    except (ValueError, WebhookEncryptionError) as e:
        logger.error("Failed to encrypt webhook secret: %s", e)
        raise WebhookEncryptionError(f"Encryption failed: {e}") from e


def decrypt_webhook_secret(encrypted: str) -> str:
    """Decrypt a webhook secret encrypted with AES-256-GCM.

    Args:
        encrypted: Base64-encoded string containing nonce + ciphertext + tag.

    Returns:
        The decrypted webhook secret.

    Raises:
        WebhookEncryptionError: If decryption fails.
    """
    if not encrypted:
        return ""

    try:
        key = _get_encryption_key()
        combined = base64.b64decode(encrypted.encode("utf-8"))

        if len(combined) < NONCE_SIZE:
            raise WebhookEncryptionError("Encrypted data too short")

        nonce = combined[:NONCE_SIZE]
        ciphertext = combined[NONCE_SIZE:]

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except (ValueError, binascii.Error, WebhookEncryptionError) as e:
        logger.error("Failed to decrypt webhook secret: %s", e)
        raise WebhookEncryptionError(f"Decryption failed: {e}") from e
