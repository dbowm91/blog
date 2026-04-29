"""Backup encryption utilities using GPG symmetric encryption.

Uses the `gnupg` library for GPG operations, with fallback to subprocess
calling the `gpg` command-line tool if the library is not available.

Encryption key is derived from the BACKUP_ENCRYPTION_KEY environment variable.
If not set, no encryption is applied.

Usage:
    # Encrypt a backup file
    encrypted_data = encrypt_backup(open("blog_20260101.db", "rb").read())
    open("blog_20260101.db.gpg", "wb").write(encrypted_data)

    # Decrypt a backup file
    decrypted_data = decrypt_backup(open("blog_20260101.db.gpg", "rb").read())
    open("blog_20260101.db", "wb").write(decrypted_data)
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

BACKUP_ENCRYPTION_KEY = os.environ.get("BACKUP_ENCRYPTION_KEY", "")


def _get_cipher_algo() -> str:
    """Get the GPG cipher algorithm. AES256 is the default."""
    return os.environ.get("BACKUP_GPG_CIPHER", "AES256")


def _derive_key(password: str) -> bytes:
    """Derive a GPG-compatible key from the password using SHA-256.

    GPG expects a passphrase, not a raw key. We use the password directly
    but ensure it meets minimum length requirements.
    """
    if len(password) < 8:
        raise ValueError(
            "BACKUP_ENCRYPTION_KEY must be at least 8 characters for GPG encryption"
        )
    return password.encode("utf-8")


def _has_gnupg() -> bool:
    """Check if the gnupg library is available."""
    try:
        import gnupg
        return True
    except ImportError:
        return False


def encrypt_backup(data: bytes, filename: str = "backup.db") -> bytes:
    """Encrypt backup data using GPG symmetric encryption.

    Args:
        data: The raw backup bytes to encrypt
        filename: Optional filename hint for GPG (stored in metadata)

    Returns:
        Encrypted bytes (ASCII-armored GPG output)

    Raises:
        RuntimeError: If GPG is not available or encryption fails
    """
    if not BACKUP_ENCRYPTION_KEY:
        raise RuntimeError(
            "BACKUP_ENCRYPTION_KEY environment variable is not set. "
            "Cannot encrypt backup."
        )

    try:
        import gnupg

        key = _derive_key(BACKUP_ENCRYPTION_KEY)
        gpg = gnupg.GPG()
        gpg.encoding = "utf-8"

        encrypted = gpg.encrypt(
            data,
            recipients=None,
            symmetric=True,
            passphrase=BACKUP_ENCRYPTION_KEY,
            cipher_algo=_get_cipher_algo(),
            protect=True,
            passphrase_from_environment=False,
        )

        if not encrypted.ok:
            raise RuntimeError(f"GPG encryption failed: {encrypted.status}")

        return bytes(encrypted.data)

    except ImportError:
        return _encrypt_backup_subprocess(data, filename)


def _encrypt_backup_subprocess(data: bytes, filename: str) -> bytes:
    """Encrypt using the gpg command-line tool (fallback when gnupg not available)."""
    key = _derive_key(BACKUP_ENCRYPTION_KEY)

    env = os.environ.copy()
    env["GPG_TTY"] = "tty"

    process = subprocess.Popen(
        [
            "gpg",
            "--batch",
            "--symmetric",
            "--passphrase-fd", "0",
            "--cipher-algo", _get_cipher_algo(),
            "--armor",
            "--compress-algo", "none",
            "-o", "-",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    stdout, stderr = process.communicate(input=BACKUP_ENCRYPTION_KEY.encode("utf-8"))

    if process.returncode != 0:
        raise RuntimeError(f"GPG encryption failed: {stderr.decode('utf-8', errors='replace')}")

    return stdout


def decrypt_backup(data: bytes) -> bytes:
    """Decrypt GPG-encrypted backup data.

    Args:
        data: Encrypted bytes (ASCII-armored or binary GPG input)

    Returns:
        Decrypted raw backup bytes

    Raises:
        RuntimeError: If GPG is not available or decryption fails
    """
    if not BACKUP_ENCRYPTION_KEY:
        raise RuntimeError(
            "BACKUP_ENCRYPTION_KEY environment variable is not set. "
            "Cannot decrypt backup."
        )

    try:
        import gnupg

        gpg = gnupg.GPG()
        gpg.encoding = "utf-8"

        decrypted = gpg.decrypt(
            data,
            passphrase=BACKUP_ENCRYPTION_KEY,
            passphrase_from_environment=False,
        )

        if not decrypted.ok:
            raise RuntimeError(f"GPG decryption failed: {decrypted.status}")

        return bytes(decrypted.data)

    except ImportError:
        return _decrypt_backup_subprocess(data)


def _decrypt_backup_subprocess(data: bytes) -> bytes:
    """Decrypt using the gpg command-line tool (fallback when gnupg not available)."""
    env = os.environ.copy()
    env["GPG_TTY"] = "tty"

    process = subprocess.Popen(
        [
            "gpg",
            "--batch",
            "--decrypt",
            "--passphrase-fd", "0",
            "--armor",
            "-o", "-",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    stdout, stderr = process.communicate(input=BACKUP_ENCRYPTION_KEY.encode("utf-8"))

    if process.returncode != 0:
        raise RuntimeError(f"GPG decryption failed: {stderr.decode('utf-8', errors='replace')}")

    return stdout


def is_encryption_available() -> bool:
    """Check if backup encryption is available (GPG and key configured)."""
    if not BACKUP_ENCRYPTION_KEY:
        return False

    try:
        import gnupg
        return True
    except ImportError:
        try:
            result = subprocess.run(
                ["gpg", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False


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
    except Exception as e:
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
    except Exception as e:
        logger.error("Failed to decrypt backup file %s: %s", input_path, e)
        return False
