"""Service layer for shared business logic."""

from app.services.backup import create_backup, cleanup_old_backups, run_daily_backup, decrypt_backup_file
from app.services.slug import generate_unique_slug
from app.services.serialization import (
    serialize_post,
    serialize_subscriber,
    serialize_page,
    serialize_tag,
    export_data_to_dict,
)
from app.services.tag import (
    get_or_create_tags,
    get_tag_by_slug,
    get_all_tags,
    get_tag_post_count,
    delete_tag_if_unused,
)

__all__ = [
    "create_backup",
    "cleanup_old_backups",
    "run_daily_backup",
    "decrypt_backup_file",
    "generate_unique_slug",
    "serialize_post",
    "serialize_subscriber",
    "serialize_page",
    "serialize_tag",
    "export_data_to_dict",
    "get_or_create_tags",
    "get_tag_by_slug",
    "get_all_tags",
    "get_tag_post_count",
    "delete_tag_if_unused",
]
