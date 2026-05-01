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
import os
import sys
from pathlib import Path


def get_db_path():
    """Get the database path."""
    return os.path.join("instance", "blog.db")


def main():
    from app.services.backup import create_backup, decrypt_backup_file

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
