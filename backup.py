#!/usr/bin/env python3
"""SQLite backup utility for DevLog blog.

Creates timestamped backups of the SQLite database using the .backup API.
Supports compression and retention policy.

Usage:
    python backup.py                    # Create backup
    python backup.py --compress         # Create compressed backup
    python backup.py --keep 5           # Keep only last 5 backups
    python backup.py --compress --keep 3 # Compressed, keep last 3
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
    """Get the database path from config or default location."""
    # Try to import from app config
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from app.config import _config
        instance_path = _config.get("app", {}).get("instance_path", "instance")
        return os.path.join(instance_path, "blog.db")
    except Exception:
        pass
    # Fallback to default location
    return os.path.join("instance", "blog.db")


def create_backup(db_path, backup_dir, compress=False, keep=7):
    """Create a backup of the SQLite database.
    
    Args:
        db_path: Path to the source database
        backup_dir: Directory to store backups
        compress: Whether to compress the backup with gzip
        keep: Number of backups to retain (default: 7)
    
    Returns:
        Path to the created backup file, or None on failure
    """
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return None
    
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"blog_{timestamp}.db"
    if compress:
        backup_name += ".gz"
    backup_path = os.path.join(backup_dir, backup_name)
    
    try:
        # Use SQLite's backup API for consistent snapshot
        source = sqlite3.connect(db_path)
        dest = sqlite3.connect(backup_path if not compress else ":memory:")
        
        try:
            source.backup(dest)
        finally:
            dest.close()
            source.close()
        
        # Compress if requested
        if compress:
            with open(backup_path, "rb") as f_in:
                with gzip.open(backup_path + ".tmp", "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.replace(backup_path + ".tmp", backup_path)
        
        print(f"Backup created: {backup_path}")
        
        # Clean up old backups
        cleanup_old_backups(backup_dir, keep)
        
        return backup_path
        
    except Exception as e:
        print(f"Error creating backup: {e}")
        # Clean up partial backup
        if os.path.exists(backup_path):
            os.remove(backup_path)
        return None


def cleanup_old_backups(backup_dir, keep):
    """Remove old backups, keeping only the most recent ones."""
    backup_files = []
    for f in os.listdir(backup_dir):
        if f.startswith("blog_") and (f.endswith(".db") or f.endswith(".db.gz")):
            full_path = os.path.join(backup_dir, f)
            backup_files.append((os.path.getmtime(full_path), full_path))
    
    # Sort by modification time, newest first
    backup_files.sort(reverse=True)
    
    # Remove old backups
    for _, path in backup_files[keep:]:
        os.remove(path)
        print(f"Removed old backup: {path}")


def main():
    parser = argparse.ArgumentParser(description="Create SQLite backup for DevLog")
    parser.add_argument("--compress", action="store_true", help="Compress backup with gzip")
    parser.add_argument("--keep", type=int, default=7, help="Number of backups to retain (default: 7)")
    parser.add_argument("--db", type=str, help="Path to database file (default: instance/blog.db)")
    parser.add_argument("--dir", type=str, default="backups", help="Backup directory (default: backups)")
    
    args = parser.parse_args()
    
    db_path = args.db or get_db_path()
    backup_dir = args.dir
    
    print(f"Database: {db_path}")
    print(f"Backup directory: {backup_dir}")
    print(f"Compression: {'enabled' if args.compress else 'disabled'}")
    print(f"Retention: {args.keep} backups")
    print()
    
    result = create_backup(db_path, backup_dir, args.compress, args.keep)
    
    if result:
        print("\nBackup completed successfully!")
        return 0
    else:
        print("\nBackup failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
