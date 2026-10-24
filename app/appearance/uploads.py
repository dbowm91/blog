"""Persistence for operator supplied fonts and backdrops.

Uploads are written through the configured storage backend, so a deployment
that stores media in S3 keeps its fonts and backdrops there too.  Every file
is validated before it is written and every name is derived from the upload,
never from the request.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

from app.appearance.backdrops import CUSTOM_BACKDROP_PREFIX
from app.appearance.fonts import CUSTOM_FONT_PREFIX
from app.appearance.svg import SvgSanitisationError, sanitize_svg

logger = logging.getLogger(__name__)

MAX_FONT_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_BACKDROP_UPLOAD_BYTES = 1024 * 1024

FONT_SIGNATURES: dict[str, bytes] = {
    ".woff2": b"wOF2",
    ".woff": b"wOFF",
}


def _slugify(filename: str) -> str:
    from app.utils import generate_slug

    stem = os.path.splitext(os.path.basename(filename))[0]
    return generate_slug(stem)


def _store(storage: Any, filename: str, data: bytes) -> str:
    storage.save(filename, data)
    return filename


def save_custom_font(storage: Any, upload: Any) -> tuple[str | None, str | None]:
    """Store an uploaded font file.

    Returns ``(filename, None)`` on success and ``(None, message)`` when the
    upload is rejected.
    """
    original = getattr(upload, "filename", "") or ""
    extension = os.path.splitext(original)[1].lower()
    signature = FONT_SIGNATURES.get(extension)
    if signature is None:
        return None, "The font must be a .woff2 or .woff file."

    data = upload.read()
    if not data:
        return None, "The uploaded font file is empty."
    if len(data) > MAX_FONT_UPLOAD_BYTES:
        return None, "The font file is larger than the 5 MB limit."
    if not data.startswith(signature):
        return None, "The uploaded file is not a valid woff2 font."

    digest = hashlib.sha256(data).hexdigest()[:8]
    filename = f"{CUSTOM_FONT_PREFIX}{_slugify(original)}-{digest}{extension}"
    try:
        return _store(storage, filename, data), None
    except Exception:
        logger.exception("appearance: failed to store the uploaded font")
        return None, "The font file could not be saved."


def save_custom_backdrop(storage: Any, upload: Any) -> tuple[str | None, str | None]:
    """Store an uploaded SVG backdrop.

    The document is sanitised before it is written, so the stored file cannot
    carry scripting or external references.
    """
    original = getattr(upload, "filename", "") or ""
    extension = os.path.splitext(original)[1].lower()
    if extension != ".svg":
        return None, "The backdrop must be an .svg file."

    data = upload.read()
    if not data:
        return None, "The uploaded backdrop file is empty."
    if len(data) > MAX_BACKDROP_UPLOAD_BYTES:
        return None, "The backdrop file is larger than the 1 MB limit."

    try:
        cleaned = sanitize_svg(data.decode("utf-8", errors="replace"))
    except SvgSanitisationError as exc:
        return None, f"The backdrop could not be sanitised: {exc}"
    except UnicodeDecodeError:
        return None, "The backdrop must be a UTF-8 encoded SVG document."

    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:8]
    filename = f"{CUSTOM_BACKDROP_PREFIX}{_slugify(original)}-{digest}.svg"
    try:
        return _store(storage, filename, cleaned.encode("utf-8")), None
    except Exception:
        logger.exception("appearance: failed to store the uploaded backdrop")
        return None, "The backdrop file could not be saved."


__all__ = [
    "FONT_SIGNATURES",
    "MAX_BACKDROP_UPLOAD_BYTES",
    "MAX_FONT_UPLOAD_BYTES",
    "save_custom_backdrop",
    "save_custom_font",
]
