"""Backup encryption utilities using PBKDF2-HMAC-SHA256 with AES encryption.

Implements NIST SP 800-132 compliant key derivation using PBKDF2-HMAC-SHA256
with 600,000 iterations and a 16-byte random salt.

The encrypted format is: salt(16 bytes) + nonce(12 bytes) + ciphertext + tag(16 bytes)
Uses AES-256-GCM for authenticated encryption.

Encryption key is derived from the BACKUP_ENCRYPTION_KEY environment variable.
If not set, no encryption is applied.

Usage:
    # Encrypt a backup file
    encrypted_data = encrypt_backup(open("blog_20260101.db", "rb").read())
    open("blog_20260101.db.enc", "wb").write(encrypted_data)

    # Decrypt a backup file
    decrypted_data = decrypt_backup(open("blog_20260101.db.enc", "rb").read())
    open("blog_20260101.db", "wb").write(decrypted_data)
"""

from __future__ import annotations

import hashlib
import logging
import os

from sqlalchemy.exc import SQLAlchemyError

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

logger = logging.getLogger(__name__)

BACKUP_ENCRYPTION_KEY = os.environ.get("BACKUP_ENCRYPTION_KEY", "")

# NIST SP 800-132 recommended iterations for PBKDF2-HMAC-SHA256
PBKDF2_ITERATIONS = 600_000
SALT_SIZE = 16  # 16-byte salt as per NIST SP 800-132
KEY_SIZE = 32  # 256-bit key for AES-256
NONCE_SIZE = 12  # 12-byte nonce for AES-GCM (recommended size)


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit encryption key from password using PBKDF2-HMAC-SHA256.

    Uses NIST SP 800-132 recommended parameters:
    - PBKDF2 with HMAC-SHA256
    - 600,000 iterations
    - 16-byte random salt
    - 256-bit output key for AES-256

    Args:
        password: The user-provided password (BACKUP_ENCRYPTION_KEY)
        salt: 16-byte random salt value

    Returns:
        32-byte derived key

    Raises:
        ValueError: If password is too short or salt is invalid
    """
    if len(password) < 12:
        raise ValueError("BACKUP_ENCRYPTION_KEY must be at least 12 characters for encryption")
    if len(salt) != SALT_SIZE:
        raise ValueError(f"Salt must be exactly {SALT_SIZE} bytes")

    # Use hashlib's pbkdf2_hmac (available in stdlib)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=KEY_SIZE,
    )
    return key


def _has_gnupg() -> bool:
    """Check if cryptography library is available (kept for backward compatibility)."""
    return CRYPTOGRAPHY_AVAILABLE


def encrypt_backup(data: bytes, filename: str = "backup.db") -> bytes:
    """Encrypt backup data using AES-256-GCM with PBKDF2 key derivation.

    Args:
        data: The raw backup bytes to encrypt
        filename: Optional filename hint (unused, kept for compatibility)

    Returns:
        Encrypted bytes (salt + nonce + ciphertext + tag)

    Raises:
        RuntimeError: If encryption is not available or encryption fails
        ValueError: If BACKUP_ENCRYPTION_KEY is not set or too short
    """
    if not BACKUP_ENCRYPTION_KEY:
        raise ValueError(
            "BACKUP_ENCRYPTION_KEY environment variable is not set. Cannot encrypt backup."
        )

    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError(
            "cryptography library is not available. Install with: pip install cryptography"
        )

    try:
        # Generate random salt and nonce
        salt = os.urandom(SALT_SIZE)
        nonce = os.urandom(NONCE_SIZE)

        # Derive key using PBKDF2-HMAC-SHA256
        key = _derive_key(BACKUP_ENCRYPTION_KEY, salt)

        # Encrypt using AES-256-GCM
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()

        # Output format: salt + nonce + ciphertext + tag
        return salt + nonce + ciphertext + encryptor.tag

    except (OSError, ValueError, SQLAlchemyError) as e:
        raise RuntimeError(f"Encryption failed: {e}")


def decrypt_backup(data: bytes) -> bytes:
    """Decrypt backup data encrypted with AES-256-GCM and PBKDF2 key derivation.

    Args:
        data: Encrypted bytes (salt + nonce + ciphertext + tag)

    Returns:
        Decrypted raw backup bytes

    Raises:
        RuntimeError: If decryption fails
        ValueError: If BACKUP_ENCRYPTION_KEY is not set or data is invalid
    """
    if not BACKUP_ENCRYPTION_KEY:
        raise ValueError(
            "BACKUP_ENCRYPTION_KEY environment variable is not set. Cannot decrypt backup."
        )

    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError(
            "cryptography library is not available. Install with: pip install cryptography"
        )

    try:
        # Minimum size check: salt(16) + nonce(12) + tag(16) = 44 bytes minimum
        if len(data) < SALT_SIZE + NONCE_SIZE + 16:
            raise ValueError("Encrypted data is too short to be valid")

        # Extract components
        salt = data[:SALT_SIZE]
        nonce = data[SALT_SIZE : SALT_SIZE + NONCE_SIZE]
        tag = data[-16:]
        ciphertext = data[SALT_SIZE + NONCE_SIZE : -16]

        # Derive key using PBKDF2-HMAC-SHA256
        key = _derive_key(BACKUP_ENCRYPTION_KEY, salt)

        # Decrypt using AES-256-GCM
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        return plaintext

    except (OSError, ValueError, SQLAlchemyError) as e:
        raise RuntimeError(f"Decryption failed: {e}")


def is_encryption_available() -> bool:
    """Check if backup encryption is available (library installed and key configured)."""
    return CRYPTOGRAPHY_AVAILABLE and bool(BACKUP_ENCRYPTION_KEY)


def encrypt_backup_file(input_path: str, output_path: str) -> bool:
    """Encrypt a backup file and write to output path.

    Args:
        input_path: Path to the unencrypted backup file
        output_path: Path to write the encrypted output

    Returns:
        True on success, False on failure
    """
    try:
        with open(input_path, "rb") as f:
            data = f.read()

        encrypted = encrypt_backup(data, os.path.basename(input_path))

        with open(output_path, "wb") as f:
            f.write(encrypted)

        return True
    except (OSError, ValueError, SQLAlchemyError) as e:
        logger.error("Failed to encrypt backup file %s: %s", input_path, e)
        return False


def decrypt_backup_file(input_path: str, output_path: str) -> bool:
    """Decrypt a backup file and write to output path.

    Args:
        input_path: Path to the encrypted backup file
        output_path: Path to write the decrypted output

    Returns:
        True on success, False on failure
    """
    try:
        with open(input_path, "rb") as f:
            data = f.read()

        decrypted = decrypt_backup(data)

        with open(output_path, "wb") as f:
            f.write(decrypted)

        return True
    except (OSError, ValueError, SQLAlchemyError) as e:
        logger.error("Failed to decrypt backup file %s: %s", input_path, e)
        return False
