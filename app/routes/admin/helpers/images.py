"""Image handling helpers for admin routes."""

import os
import uuid
from typing import Optional

from PIL import Image
from flask import current_app
from werkzeug.datastructures import FileStorage

from app.routes.admin.helpers.shared import ALLOWED_EXTENSIONS
from app.config import MAX_UPLOAD_SIZE


def _detect_image_type(header: bytes) -> Optional[str]:
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if header[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if header[:3] == b"GIF" and header[3:6] in (b"87a", b"89a"):
        return "gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _save_image(
    file: FileStorage,
) -> tuple[str, None] | tuple[None, str] | tuple[None, None]:
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
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        _generate_responsive_variants(filepath, ext)
        return filename, None
    return None, None


def _generate_responsive_variants(filepath: str, ext: str):
    for width in (400, 800, 1200):
        variant_filename = f"{width}_{os.path.basename(filepath)}"
        variant_path = os.path.join(os.path.dirname(filepath), variant_filename)
        try:
            with Image.open(filepath) as img:
                if img.width > width:
                    ratio = width / img.width
                    new_height = int(img.height * ratio)
                    img.resize((width, new_height), Image.LANCZOS).save(
                        variant_path, optimize=True
                    )
        except Exception:
            pass
