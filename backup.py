#!/usr/bin/env python3
"""SQLite backup utility for DevLog blog.

Creates timestamped backups of the SQLite database using the .backup API.
Supports compression, GPG encryption, and retention policy.

Usage:
    python backup.py                    # Create backup
    python backup.py --compress         # Create compressed backup
    python backup.py --encrypt          # Create encrypted backup
    python backup.py --compress --encrypt  # Compressed and encrypted
    python backup.py --keep 5           # Keep only last 5 backups
    python backup.py --decrypt backup.db.gpg  # Decrypt a backup file
"""

import argparse
import gzip
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def get_db_path():
    """Get the database path."""
    return os.path.join("instance", "blog.db")


def create_backup(db_path, backup_dir, compress=False, keep=7, encrypt=False):
    """Create a backup of the SQLite database.

    Args:
        db_path: Path to the source database
        backup_dir: Directory to store backups
        compress: Whether to compress the backup with gzip
        keep: Number of backups to retain (default: 7)
        encrypt: Whether to encrypt the backup with GPG

    Returns:
        Path to the created backup file, or None on failure
    """
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return None

    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"blog_{timestamp}.db"
    if compress:
        backup_name += ".gz"
    if encrypt:
        backup_name += ".gpg"
    backup_path = os.path.join(backup_dir, backup_name)

    try:
        source = sqlite3.connect(db_path)
        dest = sqlite3.connect(backup_path)

        try:
            source.backup(dest)
        finally:
            dest.close()
            source.close()

        if encrypt:
            if not _encrypt_backup_file(backup_path):
                print(f"Error: Failed to encrypt backup")
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                return None
        elif compress:
            tmp_path = backup_path + ".tmp"
            try:
                with open(backup_path, "rb") as f_in:
                    with gzip.open(tmp_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.replace(tmp_path, backup_path)
            except OSError:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise

        print(f"Backup created: {backup_path}")

        cleanup_old_backups(backup_dir, keep)

        return backup_path

    except (sqlite3.Error, OSError) as e:
        print(f"Error creating backup: {e}")
        if os.path.exists(backup_path):
            os.remove(backup_path)
        return None


def _encrypt_backup_file(filepath: str) -> bool:
    """Encrypt a backup file using GPG.

    Requires BACKUP_ENCRYPTION_KEY environment variable.
    """
    try:
        from app.backup_encryption import encrypt_backup_file
        return encrypt_backup_file(filepath, filepath)
    except Exception as e:
        print(f"Encryption error: {e}")
        return False


def decrypt_backup_file(input_path: str, output_path: str = None) -> bool:
    """Decrypt a GPG-encrypted backup file.

    Args:
        input_path: Path to the encrypted backup file
        output_path: Path to write the decrypted output (default: input_path without .gpg extension)

    Returns:
        True on success, False on failure
    """
    try:
        from app.backup_encryption import decrypt_backup_file as _decrypt
        if output_path is None:
            if input_path.endswith(".gpg"):
                output_path = input_path[:-4]
            else:
                output_path = input_path + ".decrypted"
        return _decrypt(input_path, output_path)
    except Exception as e:
        print(f"Decryption error: {e}")
        return False


def cleanup_old_backups(backup_dir, keep):
    """Remove old backups, keeping only the most recent ones."""
    backup_files = []
    for f in os.listdir(backup_dir):
        if f.startswith("blog_") and (f.endswith(".db") or f.endswith(".db.gz") or f.endswith(".db.gpg")):
            full_path = os.path.join(backup_dir, f)
            backup_files.append((os.path.getmtime(full_path), full_path))

    backup_files.sort(reverse=True)

    for _, path in backup_files[keep:]:
        os.remove(path)
        print(f"Removed old backup: {path}")


def main():
    parser = argparse.ArgumentParser(description="Create SQLite backup for DevLog")
    parser.add_argument(
        "--compress", action="store_true", help="Compress backup with gzip"
    )
    parser.add_argument(
        "--encrypt", action="store_true", help="Encrypt backup with GPG (requires BACKUP_ENCRYPTION_KEY)"
    )
    parser.add_argument(
        "--decrypt", type=str, metavar="FILE", help="Decrypt a GPG-encrypted backup file"
    )
    parser.add_argument(
        "--keep", type=int, default=7, help="Number of backups to retain (default: 7)"
    )
    parser.add_argument(
        "--db", type=str, help="Path to database file (default: instance/blog.db)"
    )
    parser.add_argument(
        "--dir", type=str, default="backups", help="Backup directory (default: backups)"
    )

    args = parser.parse_args()

    if args.decrypt:
        output_path = args.db
        if output_path:
            success = decrypt_backup_file(args.decrypt, output_path)
        else:
            success = decrypt_backup_file(args.decrypt)
        if success:
            print("Decryption completed successfully!")
            return 0
        else:
            print("Decryption failed!")
            return 1

    if args.keep < 1:
        parser.error("--keep must be at least 1")

    db_path = args.db or get_db_path()
    backup_dir = args.dir

    print(f"Database: {db_path}")
    print(f"Backup directory: {backup_dir}")
    print(f"Compression: {'enabled' if args.compress else 'disabled'}")
    print(f"Encryption: {'enabled' if args.encrypt else 'disabled'}")
    print(f"Retention: {args.keep} backups")
    print()

    result = create_backup(db_path, backup_dir, args.compress, args.keep, args.encrypt)

    if result:
        print("\nBackup completed successfully!")
        return 0
    else:
        print("\nBackup failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
