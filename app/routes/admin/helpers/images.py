"""Image handling helpers for admin routes."""

import uuid
from typing import Optional

from werkzeug.datastructures import FileStorage

from app.routes.admin.helpers.shared import ALLOWED_EXTENSIONS
from app.config import MAX_UPLOAD_SIZE


signatures = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpeg",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"RIFF": "webp",
}


def _detect_image_type(header: bytes) -> Optional[str]:
    for sig, ext in signatures.items():
        if header.startswith(sig):
            if ext == "webp" and (len(header) < 12 or header[8:12] != b"WEBP"):
                return None
            return ext
    return None


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _save_image(
    file: FileStorage,
) -> tuple[str | None, str | None]:
    if file and file.filename and _allowed_file(file.filename):
        header = file.read(32)
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > MAX_UPLOAD_SIZE:
            return (
                None,
                f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)}MB.",
            )
        detected = _detect_image_type(header)
        if detected not in ("png", "jpeg", "gif", "webp"):
            return None, "Uploaded file is not a valid image."
        ext = detected
        filename = f"{uuid.uuid4().hex}.{ext}"
        file_content = file.read()

        from app.storage import upload_with_processing

        result_filename, error = upload_with_processing(filename, file_content)
        if error:
            return None, error
        return result_filename, None
    return None, None
