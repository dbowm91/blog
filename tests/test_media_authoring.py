from __future__ import annotations

import importlib
import io
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.storage import S3StorageBackend, StorageFileInfo
from app.routes.admin.helpers.media import classify_media


class MemoryStorage:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    def save(self, filename: str, content: bytes) -> str:
        self.files[filename] = content
        return filename

    def load(self, filename: str) -> bytes | None:
        return self.files.get(filename)

    def exists(self, filename: str) -> bool:
        return filename in self.files

    def url(self, filename: str) -> str:
        return f"/static/uploads/{filename}"

    def list_file_info(self, prefix: str = "") -> list[StorageFileInfo]:
        return [
            StorageFileInfo(
                name=name,
                size=len(content),
                mtime=datetime.now(timezone.utc),
                url=self.url(name),
            )
            for name, content in self.files.items()
            if name.startswith(prefix)
        ]

    def read_header(self, filename: str, length: int = 32) -> bytes:
        return self.files.get(filename, b"")[:length]


def test_media_classification_requires_extension_and_content_match():
    assert classify_media("photo.png", b"\x89PNG\r\n\x1a\nrest") == "image"
    assert classify_media("clip.mp4", b"\x00\x00\x00\x18ftypisom") == "video"
    assert classify_media("clip.mp4", b"not a video") == "other"
    assert classify_media("script.html", b"<script>") == "other"
    assert classify_media("a-report.html.attachment", b"<script>") == "other"


def test_upload_api_stores_other_file_as_attachment_and_forces_download(
    authenticated_client, monkeypatch
):
    storage = MemoryStorage()
    monkeypatch.setattr("app.routes.admin.helpers.media.get_storage", lambda: storage)
    monkeypatch.setattr("app.routes.public.media.get_storage", lambda: storage)

    response = authenticated_client.post(
        "/admin/media/upload",
        data={
            "category": "other",
            "file": (io.BytesIO(b"<script>alert(1)</script>"), "report.html"),
        },
        headers={"Accept": "application/json"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    item = response.get_json()["item"]
    assert item["category"] == "other"
    assert item["display_name"] == "report.html"
    assert item["url"].startswith("/media/download/")
    assert ".attachment" in next(iter(storage.files))

    download = authenticated_client.get(item["url"])
    assert download.status_code == 200
    assert download.data == b"<script>alert(1)</script>"
    assert download.mimetype == "application/octet-stream"
    assert download.headers["Content-Disposition"].startswith("attachment;")
    assert "report.html" in download.headers["Content-Disposition"]
    assert download.headers["X-Content-Type-Options"] == "nosniff"


def test_download_route_rejects_non_attachment_storage_keys(authenticated_client, monkeypatch):
    storage = MemoryStorage()
    storage.save("private.txt", b"private object")
    monkeypatch.setattr("app.routes.public.media.get_storage", lambda: storage)

    response = authenticated_client.get("/media/download/private.txt")

    assert response.status_code == 404


def test_download_route_allows_signature_validated_video_only_as_attachment(
    authenticated_client, monkeypatch
):
    storage = MemoryStorage()
    storage.save("movie.mp4", bytes((0, 0, 0, 24)) + b"ftypisom" + b"0" * 16)
    monkeypatch.setattr("app.routes.public.media.get_storage", lambda: storage)

    response = authenticated_client.get("/media/download/movie.mp4")

    assert response.status_code == 200
    assert response.headers["Content-Disposition"].startswith("attachment;")
    assert response.mimetype == "application/octet-stream"


def test_video_upload_accepts_valid_mp4_signature(authenticated_client, monkeypatch):
    storage = MemoryStorage()
    monkeypatch.setattr("app.routes.admin.helpers.media.get_storage", lambda: storage)
    body = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 16

    response = authenticated_client.post(
        "/admin/media/upload",
        data={"category": "video", "file": (io.BytesIO(body), "clip.mp4")},
        headers={"Accept": "application/json"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    item = response.get_json()["item"]
    assert item["category"] == "video"
    assert item["mime_type"] == "video/mp4"
    assert item["url"].endswith(".mp4")
    assert storage.files[item["name"]] == body


def test_upload_enforces_configured_max_size(authenticated_client, monkeypatch):
    storage = MemoryStorage()
    monkeypatch.setattr("app.routes.admin.helpers.media.get_storage", lambda: storage)
    monkeypatch.setattr("app.routes.admin.helpers.media.MAX_UPLOAD_SIZE", 4)

    response = authenticated_client.post(
        "/admin/media/upload",
        data={"category": "other", "file": (io.BytesIO(b"12345"), "large.bin")},
        headers={"Accept": "application/json"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "too large" in response.get_json()["error"].lower()
    assert storage.files == {}


def test_upload_returns_safe_error_when_storage_fails(authenticated_client, monkeypatch):
    class BrokenStorage(MemoryStorage):
        def save(self, filename: str, content: bytes) -> str:
            raise OSError("backend failure")

    storage = BrokenStorage()
    monkeypatch.setattr("app.routes.admin.helpers.media.get_storage", lambda: storage)

    response = authenticated_client.post(
        "/admin/media/upload",
        data={"category": "other", "file": (io.BytesIO(b"data"), "notes.txt")},
        headers={"Accept": "application/json"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "The file could not be stored."}
    assert "backend failure" not in response.get_data(as_text=True)


def test_upload_requires_csrf_when_global_validation_is_enabled(app, authenticated_client):
    previous_csrf = app.config["CSRF_ENABLED"]
    previous_testing = app.config["TESTING"]
    app.config["CSRF_ENABLED"] = True
    app.config["TESTING"] = False
    try:
        response = authenticated_client.post(
            "/admin/media/upload",
            data={"category": "other", "file": (io.BytesIO(b"data"), "notes.txt")},
            headers={"Accept": "application/json"},
            content_type="multipart/form-data",
        )
    finally:
        app.config["CSRF_ENABLED"] = previous_csrf
        app.config["TESTING"] = previous_testing

    assert response.status_code == 403


def test_video_upload_rejects_mismatched_signature(authenticated_client, monkeypatch):
    storage = MemoryStorage()
    monkeypatch.setattr("app.routes.admin.helpers.media.get_storage", lambda: storage)

    response = authenticated_client.post(
        "/admin/media/upload",
        data={"category": "video", "file": (io.BytesIO(b"not video"), "clip.mp4")},
        headers={"Accept": "application/json"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert storage.files == {}


def test_editor_media_items_returns_validated_categories(authenticated_client, monkeypatch):
    storage = MemoryStorage()
    storage.save("picture.png", b"\x89PNG\r\n\x1a\n" + b"0" * 16)
    storage.save("movie.mp4", b"\x00\x00\x00\x18ftypisom")
    storage.save("0123456789abcdef0123456789abcdef-document.attachment", b"document")
    storage.save("legacy.txt", b"old unclassified object")
    monkeypatch.setattr("app.routes.admin.helpers.media.get_storage", lambda: storage)
    monkeypatch.setattr("app.storage.get_storage", lambda: storage)
    media_module = importlib.import_module("app.routes.admin.media")
    monkeypatch.setattr(media_module, "_MEDIA_CACHE", {"files": None, "timestamp": 0})

    response = authenticated_client.get("/admin/media/items")

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert {item["category"] for item in items} == {"image", "video", "other"}
    video = next(item for item in items if item["name"] == "movie.mp4")
    assert video["mime_type"] == "video/mp4"
    page = authenticated_client.get("/admin/media")
    assert page.status_code == 200
    page_html = page.get_data(as_text=True)
    assert "Images (1)" in page_html
    assert "Videos (1)" in page_html
    assert "Other (2)" in page_html
    legacy = next(item for item in items if item["name"] == "legacy.txt")
    assert legacy["category"] == "other"
    assert legacy["url"] is None
    assert legacy["download_url"] is None
    attachment = next(item for item in items if item["name"].endswith("-document.attachment"))
    assert attachment["url"].startswith("/media/download/")
    monkeypatch.setattr("app.routes.public.media.get_storage", lambda: storage)
    download = authenticated_client.get(attachment["url"])
    assert download.status_code == 200
    assert download.mimetype == "application/octet-stream"
    assert download.headers["Content-Disposition"].startswith("attachment;")


def test_s3_attachment_upload_sets_download_content_headers():
    storage = S3StorageBackend("bucket", public_url="https://media.example")
    storage._client = MagicMock()

    storage.save("0123456789abcdef0123456789abcdef-report.html.attachment", b"data")

    storage.client.put_object.assert_called_once_with(
        Bucket="bucket",
        Key="0123456789abcdef0123456789abcdef-report.html.attachment",
        Body=b"data",
        ContentType="application/octet-stream",
        ContentDisposition="attachment",
    )


def test_s3_media_catalog_reads_all_pages():
    storage = S3StorageBackend("bucket")
    storage._client = MagicMock()
    storage.client.list_objects_v2.side_effect = [
        {
            "Contents": [
                {
                    "Key": "image.png",
                    "Size": 10,
                    "LastModified": datetime(2026, 10, 28, tzinfo=timezone.utc),
                }
            ],
            "IsTruncated": True,
            "NextContinuationToken": "next-page",
        },
        {
            "Contents": [
                {
                    "Key": "clip.mp4",
                    "Size": 20,
                    "LastModified": datetime(2026, 10, 29, tzinfo=timezone.utc),
                }
            ],
            "IsTruncated": False,
        },
    ]

    files = storage.list_file_info()

    assert [item.name for item in files] == ["clip.mp4", "image.png"]
    assert storage.client.list_objects_v2.call_count == 2
    assert (
        storage.client.list_objects_v2.call_args_list[1].kwargs["ContinuationToken"] == "next-page"
    )
