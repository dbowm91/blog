"""Resumable chunked upload sessions for large media files.

Single-POST uploads are bounded by ``MAX_UPLOAD_SIZE`` and read the whole
file into memory. Files larger than that - 670MB videos, for example - are
uploaded in small chunks that each fit comfortably under every body-size
cap on the path (reverse proxy, ``MAX_CONTENT_LENGTH``). The server stores
chunks on disk and streams them back together at completion, so peak RAM
stays flat no matter how large the file is.

Only ``video`` and ``other`` categories are accepted here. Images go
through the standard upload because image processing (type detection and
variant generation) inherently loads the whole file.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import tempfile
import time
import uuid
from pathlib import PurePosixPath

from flask import current_app, url_for
from werkzeug.utils import secure_filename

from app.config import CHUNKED_UPLOAD_MAX_SIZE

CHUNK_SIZE = 4 * 1024 * 1024
SESSION_DIRNAME = ".chunked"
SESSION_TTL_SECONDS = 24 * 3600
CHUNKED_CATEGORIES = ("video", "other")
_UPLOAD_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_COPY_BUFFER_SIZE = 1024 * 1024


def session_root() -> str:
    """Directory holding all in-progress chunked sessions."""
    root = os.path.join(current_app.config["UPLOAD_FOLDER"], SESSION_DIRNAME)
    os.makedirs(root, exist_ok=True)
    return root


def purge_expired_sessions(root: str | None = None) -> int:
    """Delete sessions older than the TTL; return how many were removed."""
    root = root or session_root()
    now = time.time()
    purged = 0
    try:
        entries = os.scandir(root)
    except OSError:
        return 0
    with entries:
        for entry in entries:
            if not entry.is_dir():
                continue
            try:
                if now - entry.stat().st_mtime <= SESSION_TTL_SECONDS:
                    continue
                shutil.rmtree(entry.path, ignore_errors=True)
                purged += 1
            except OSError:
                continue
    return purged


def expected_chunk_size(total_size: int, index: int, total_chunks: int) -> int:
    """Byte size chunk ``index`` must have."""
    if index == total_chunks - 1:
        return total_size - CHUNK_SIZE * (total_chunks - 1)
    return CHUNK_SIZE


def _meta_path(session_dir: str) -> str:
    return os.path.join(session_dir, "meta.json")


def create_session(filename: str, size: int, category: str) -> tuple[dict | None, str | None]:
    """Validate the upload intent and open a session for it."""
    if category not in CHUNKED_CATEGORIES:
        return None, "Chunked upload supports video and other files."
    if not isinstance(size, int) or size <= 0:
        return None, "Upload size must be a positive number of bytes."
    if size > CHUNKED_UPLOAD_MAX_SIZE:
        limit_mb = CHUNKED_UPLOAD_MAX_SIZE // (1024 * 1024)
        return None, f"File too large. Maximum size is {limit_mb}MB."
    original = secure_filename(PurePosixPath((filename or "").replace("\\", "/")).name)[:180]
    if not original:
        return None, "The filename is not valid."
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if category == "video" and ext not in ("mp4", "webm"):
        return None, "Supported video formats are MP4 and WebM."

    total_chunks = (size + CHUNK_SIZE - 1) // CHUNK_SIZE
    upload_id = secrets.token_urlsafe(32)
    root = session_root()
    purge_expired_sessions(root)
    session_dir = os.path.join(root, upload_id)
    os.makedirs(session_dir, exist_ok=False)
    meta = {
        "filename": original,
        "size": size,
        "category": category,
        "chunk_size": CHUNK_SIZE,
        "total_chunks": total_chunks,
        "created": time.time(),
    }
    with open(_meta_path(session_dir), "w") as f:
        json.dump(meta, f)
    return {"upload_id": upload_id, **meta}, None


def get_session(upload_id: str) -> tuple[str, dict] | None:
    """Return the session directory and metadata, or None when unknown."""
    if not _UPLOAD_ID_RE.match(upload_id or ""):
        return None
    session_dir = os.path.join(session_root(), upload_id)
    if not os.path.isdir(session_dir):
        return None
    try:
        with open(_meta_path(session_dir)) as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(meta, dict):
        return None
    return session_dir, meta


def received_mask(session_dir: str, meta: dict) -> list[bool]:
    """Which chunks are on disk with the exact expected size."""
    total_chunks = int(meta["total_chunks"])
    total_size = int(meta["size"])
    mask = []
    for index in range(total_chunks):
        part = os.path.join(session_dir, f"{index}.part")
        try:
            ok = os.path.getsize(part) == expected_chunk_size(total_size, index, total_chunks)
        except OSError:
            ok = False
        mask.append(ok)
    return mask


def write_chunk(upload_id: str, index: int, data: bytes) -> tuple[int | None, str | None]:
    """Store one chunk; return the count of chunks received so far."""
    found = get_session(upload_id)
    if found is None:
        return None, "Unknown or expired upload."
    session_dir, meta = found
    total_chunks = int(meta["total_chunks"])
    if index < 0 or index >= total_chunks:
        return None, "Chunk index out of range."
    if len(data) != expected_chunk_size(int(meta["size"]), index, total_chunks):
        return None, "Chunk size does not match the upload plan."
    part = os.path.join(session_dir, f"{index}.part")
    tmp = f"{part}.{os.getpid()}.tmp"
    try:
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, part)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return None, "The chunk could not be stored."
    mask = received_mask(session_dir, meta)
    return sum(mask), None


def abort_session(upload_id: str) -> bool:
    """Delete a session and its chunks; False when it did not exist."""
    if not _UPLOAD_ID_RE.match(upload_id or ""):
        return False
    session_dir = os.path.join(session_root(), upload_id)
    if not os.path.isdir(session_dir):
        return False
    shutil.rmtree(session_dir, ignore_errors=True)
    return True


def assemble_session(upload_id: str) -> tuple[str, dict, str | None]:
    """Stream all chunks into one temp file; verify size and content type.

    Returns the temp file path and the session metadata. The caller owns
    the temp file and must delete it when done.
    """
    from app.routes.admin.helpers.media import classify_media

    found = get_session(upload_id)
    if found is None:
        return "", {}, "Unknown or expired upload."
    session_dir, meta = found
    total_chunks = int(meta["total_chunks"])
    total_size = int(meta["size"])
    category = meta["category"]

    mask = received_mask(session_dir, meta)
    if not all(mask):
        missing = sum(1 for ok in mask if not ok)
        return "", {}, f"Upload incomplete: {missing} of {total_chunks} chunks missing."

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    fd, tmp_path = tempfile.mkstemp(dir=upload_dir, prefix=".assembling-")
    header = b""
    try:
        with os.fdopen(fd, "wb") as out:
            for index in range(total_chunks):
                part = os.path.join(session_dir, f"{index}.part")
                with open(part, "rb") as part_file:
                    while True:
                        buf = part_file.read(_COPY_BUFFER_SIZE)
                        if not buf:
                            break
                        if len(header) < 32:
                            header = (header + buf)[:32]
                        out.write(buf)
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return "", {}, "The upload could not be assembled."

    if os.path.getsize(tmp_path) != total_size:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return "", {}, "Assembled size does not match the upload plan."
    if classify_media(meta["filename"], header) != category:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        if category == "video":
            return "", {}, "The video content does not match its file type."
        return "", {}, "The file content does not match its category."
    return tmp_path, meta, None


def finalize_upload(upload_id: str) -> tuple[dict | None, str | None]:
    """Assemble a complete session and store it; the session is removed."""
    from app.storage import get_storage

    tmp_path, meta, error = assemble_session(upload_id)
    if error or not tmp_path:
        return None, error or "Upload failed."
    category = meta["category"]
    original = meta["filename"]
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if category == "video":
        stored_name = f"{uuid.uuid4().hex}.{ext}"
    else:
        stored_name = f"{uuid.uuid4().hex}-{original}.attachment"
    storage = get_storage()
    try:
        storage.save_path(stored_name, tmp_path)
    except Exception:
        try:
            storage.delete(stored_name)
        except Exception:
            pass
        current_app.logger.exception("Chunked upload storage failed; upload_id=%s", upload_id)
        return None, "The file could not be stored."
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        abort_session(upload_id)

    if category == "video":
        url = storage.url(stored_name)
    else:
        url = url_for("public.download_media", filename=stored_name)
    return {
        "name": stored_name,
        "display_name": original if category == "other" else stored_name,
        "category": category,
        "mime_type": f"video/{ext}" if category == "video" else "application/octet-stream",
        "url": url,
    }, None
