"""Media upload validation and catalog classification."""

from __future__ import annotations

import mimetypes
import re
import uuid
from pathlib import PurePosixPath

from flask import current_app, url_for
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.config import MAX_UPLOAD_SIZE
from app.routes.admin.helpers.images import _save_image
from app.storage import get_storage

_VIDEO_SIGNATURES = {"mp4": (4, b"ftyp"), "webm": (0, b"\x1aE\xdf\xa3")}
_ATTACHMENT_RE = re.compile(r"^[0-9a-f]{32}-(.+)\.attachment$")
_VARIANT_RE = re.compile(r"^(?:400_|800_|1200_)")


def classify_media(filename: str, header: bytes = b"") -> str:
    """Classify a media key; unknown or conflicting types are never inline."""
    name = PurePosixPath(filename).name
    match = _ATTACHMENT_RE.fullmatch(name)
    if match:
        return "other"

    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    image_signatures = {
        "png": b"\x89PNG\r\n\x1a\n",
        "jpg": b"\xff\xd8\xff",
        "jpeg": b"\xff\xd8\xff",
        "gif": (b"GIF87a", b"GIF89a"),
        "webp": b"RIFF",
    }
    signature = image_signatures.get(ext)
    if signature:
        signatures = signature if isinstance(signature, tuple) else (signature,)
        if any(header.startswith(sig) for sig in signatures):
            if ext != "webp" or (len(header) >= 12 and header[8:12] == b"WEBP"):
                return "image"
        return "other"

    if ext in _VIDEO_SIGNATURES:
        offset, signature_bytes = _VIDEO_SIGNATURES[ext]
        if header[offset : offset + len(signature_bytes)] == signature_bytes:
            return "video"
        return "other"

    return "other"


def read_media_header(filename: str) -> bytes:
    """Read a small prefix without fetching the full S3 object when possible."""
    storage = get_storage()
    if hasattr(storage, "read_header"):
        return storage.read_header(filename)
    content = storage.load(filename)
    return content[:32] if content else b""


def media_display_name(filename: str) -> str:
    match = _ATTACHMENT_RE.fullmatch(PurePosixPath(filename).name)
    return match.group(1) if match else PurePosixPath(filename).name


def upload_media_file(file: FileStorage, category: str) -> tuple[dict[str, str] | None, str | None]:
    """Validate and store an image, MP4/WebM video, or arbitrary attachment."""
    if not file.filename:
        return None, "Choose a file to upload."
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size <= 0:
        return None, "The selected file is empty."
    if size > MAX_UPLOAD_SIZE:
        return None, f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)}MB."

    if category == "image":
        stored_name, error = _save_image(file)
        if error or not stored_name:
            return None, error or "Choose a supported PNG, JPEG, GIF, or WebP image."
        return {
            "name": stored_name,
            "display_name": stored_name,
            "category": "image",
            "url": get_storage().url(stored_name),
        }, None

    original_name = secure_filename(PurePosixPath(file.filename.replace("\\", "/")).name)[:180]
    if not original_name:
        return None, "The filename is not valid."
    content = file.read()
    header = content[:32]

    if category == "video":
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        if ext not in _VIDEO_SIGNATURES:
            return None, "Supported video formats are MP4 and WebM."
        offset, signature_bytes = _VIDEO_SIGNATURES[ext]
        if header[offset : offset + len(signature_bytes)] != signature_bytes:
            return None, "The video content does not match its file type."
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        actual_category = "video"
    elif category == "other":
        stored_name = f"{uuid.uuid4().hex}-{original_name}.attachment"
        actual_category = "other"
    else:
        return None, "Choose a valid media category."

    storage = get_storage()
    try:
        storage.save(stored_name, content)
    except Exception:
        try:
            storage.delete(stored_name)
        except Exception:
            pass
        current_app.logger.exception("Media upload storage failed; category=%s", category)
        return None, "The file could not be stored."

    if actual_category == "other":
        url = url_for("public.download_media", filename=stored_name)
    else:
        url = storage.url(stored_name)
    return {
        "name": stored_name,
        "display_name": original_name if actual_category == "other" else stored_name,
        "category": actual_category,
        "mime_type": f"video/{ext}" if actual_category == "video" else "application/octet-stream",
        "url": url,
    }, None


def classify_file_info(info) -> dict[str, object]:
    category = (
        "other"
        if _ATTACHMENT_RE.fullmatch(PurePosixPath(info.name).name)
        else classify_media(info.name, read_media_header(info.name))
    )
    downloadable = category in {"image", "video"} or bool(
        _ATTACHMENT_RE.fullmatch(PurePosixPath(info.name).name)
    )
    return {
        "name": info.name,
        "display_name": media_display_name(info.name),
        "category": category,
        "size": info.size,
        "mtime": info.mtime,
        "url": info.url if category in {"image", "video"} else None,
        "download_url": (
            url_for("public.download_media", filename=info.name) if downloadable else None
        ),
        "mime_type": mimetypes.guess_type(media_display_name(info.name))[0]
        or "application/octet-stream",
    }
