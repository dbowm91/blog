"""Chunked uploads assemble large media files from small resumable pieces.

A 670MB video cannot travel as one POST: the reverse proxy caps buffered
bodies at 10MB and the single-upload path caps files at ``MAX_UPLOAD_SIZE``
while reading them fully into memory. The chunked protocol keeps every
request small and streams reassembly through disk, so peak RAM stays flat
no matter how large the file is.
"""

from __future__ import annotations

import os

import pytest

import app.storage as storage_module
from app.config import CHUNKED_UPLOAD_MAX_SIZE
from app.routes.admin.helpers.chunked import CHUNK_SIZE, SESSION_DIRNAME

MP4_HEADER = b"\x00\x00\x00\x00ftyp" + b"\x00" * 24


@pytest.fixture()
def upload_folder(app, tmp_path, monkeypatch):
    """Point uploads - and the storage backend - at a scratch directory."""
    folder = tmp_path / "uploads"
    folder.mkdir()
    original_folder = app.config.get("UPLOAD_FOLDER")
    original_storage = storage_module._storage
    app.config["UPLOAD_FOLDER"] = str(folder)
    storage_module._storage = None
    yield folder
    if original_folder is None:
        app.config.pop("UPLOAD_FOLDER", None)
    else:
        app.config["UPLOAD_FOLDER"] = original_folder
    storage_module._storage = original_storage


def _start(authenticated_client, size, category="video", filename="movie.mp4"):
    return authenticated_client.post(
        "/admin/media/chunked/init",
        json={"filename": filename, "size": size, "category": category},
    )


def test_init_opens_a_session_with_a_chunk_plan(authenticated_client, upload_folder):
    response = _start(authenticated_client, CHUNK_SIZE * 2 + 100)

    assert response.status_code == 201
    plan = response.get_json()
    assert plan["chunk_size"] == CHUNK_SIZE
    assert plan["total_chunks"] == 3
    session_dir = upload_folder / SESSION_DIRNAME / plan["upload_id"]
    assert (session_dir / "meta.json").is_file()


def test_init_rejects_images(authenticated_client, upload_folder):
    response = _start(authenticated_client, 1024, category="image", filename="pic.png")

    assert response.status_code == 400
    assert "video" in response.get_json()["error"].lower()


def test_init_rejects_unsupported_video_extension(authenticated_client, upload_folder):
    response = _start(authenticated_client, 1024, filename="movie.avi")

    assert response.status_code == 400


def test_init_rejects_total_above_the_cap(authenticated_client, upload_folder):
    response = _start(authenticated_client, CHUNKED_UPLOAD_MAX_SIZE + 1)

    assert response.status_code == 400
    assert "Maximum size" in response.get_json()["error"]


def test_init_rejects_empty_uploads(authenticated_client, upload_folder):
    response = _start(authenticated_client, 0)

    assert response.status_code == 400


def test_full_roundtrip_reassembles_exact_bytes(authenticated_client, upload_folder):
    payload = MP4_HEADER + os.urandom(CHUNK_SIZE + 100 - len(MP4_HEADER))
    plan = _start(authenticated_client, len(payload)).get_json()
    upload_id = plan["upload_id"]

    for index in range(plan["total_chunks"]):
        start = index * CHUNK_SIZE
        chunk = payload[start : start + CHUNK_SIZE]
        response = authenticated_client.put(
            f"/admin/media/chunked/{upload_id}/{index}",
            data=chunk,
            content_type="application/octet-stream",
        )
        assert response.status_code == 200

    status = authenticated_client.get(f"/admin/media/chunked/{upload_id}").get_json()
    assert status["received"] == [True] * plan["total_chunks"]

    response = authenticated_client.post(f"/admin/media/chunked/{upload_id}/complete")

    assert response.status_code == 201
    item = response.get_json()["item"]
    assert item["category"] == "video"
    stored = upload_folder / item["name"]
    assert stored.read_bytes() == payload
    assert not (upload_folder / SESSION_DIRNAME / upload_id).exists()


def test_complete_refuses_missing_chunks(authenticated_client, upload_folder):
    payload = MP4_HEADER + b"\x00" * 100
    plan = _start(authenticated_client, len(payload)).get_json()

    response = authenticated_client.post(f"/admin/media/chunked/{plan['upload_id']}/complete")

    assert response.status_code == 400
    assert "incomplete" in response.get_json()["error"].lower()


def test_complete_refuses_content_that_mismatches_the_type(authenticated_client, upload_folder):
    payload = b"not a video at all" + b"\x00" * 100
    plan = _start(authenticated_client, len(payload), filename="movie.mp4").get_json()
    upload_id = plan["upload_id"]
    authenticated_client.put(
        f"/admin/media/chunked/{upload_id}/0",
        data=payload,
        content_type="application/octet-stream",
    )

    response = authenticated_client.post(f"/admin/media/chunked/{upload_id}/complete")

    assert response.status_code == 400


def test_chunk_must_match_the_plan(authenticated_client, upload_folder):
    plan = _start(authenticated_client, CHUNK_SIZE + 10).get_json()
    upload_id = plan["upload_id"]

    short = authenticated_client.put(
        f"/admin/media/chunked/{upload_id}/0",
        data=b"\x00" * 10,
        content_type="application/octet-stream",
    )
    assert short.status_code == 400

    out_of_range = authenticated_client.put(
        f"/admin/media/chunked/{upload_id}/{plan['total_chunks']}",
        data=b"\x00" * 10,
        content_type="application/octet-stream",
    )
    assert out_of_range.status_code == 400


def test_oversize_chunk_is_rejected(authenticated_client, upload_folder):
    plan = _start(authenticated_client, CHUNK_SIZE + 10).get_json()

    response = authenticated_client.put(
        f"/admin/media/chunked/{plan['upload_id']}/0",
        data=b"\x00" * (CHUNK_SIZE + 1024 * 1024 + 1),
        content_type="application/octet-stream",
    )

    assert response.status_code == 413


def test_unknown_sessions_answer_404(authenticated_client, upload_folder):
    assert authenticated_client.get("/admin/media/chunked/nope").status_code == 404
    assert (
        authenticated_client.put(
            "/admin/media/chunked/nope/0",
            data=b"\x00",
            content_type="application/octet-stream",
        ).status_code
        == 400
    )
    assert authenticated_client.post("/admin/media/chunked/nope/complete").status_code == 400
    assert authenticated_client.delete("/admin/media/chunked/nope").status_code == 404


def test_rapid_chunks_are_not_rate_limited(authenticated_client, upload_folder):
    payload = MP4_HEADER + b"\x00" * 100
    plan = _start(authenticated_client, len(payload)).get_json()
    upload_id = plan["upload_id"]

    for _ in range(105):
        response = authenticated_client.put(
            f"/admin/media/chunked/{upload_id}/0",
            data=payload,
            content_type="application/octet-stream",
        )
        assert response.status_code == 200


def test_abort_removes_the_session(authenticated_client, upload_folder):
    payload = MP4_HEADER + b"\x00" * 100
    plan = _start(authenticated_client, len(payload)).get_json()
    upload_id = plan["upload_id"]
    authenticated_client.put(
        f"/admin/media/chunked/{upload_id}/0",
        data=payload,
        content_type="application/octet-stream",
    )

    response = authenticated_client.delete(f"/admin/media/chunked/{upload_id}")

    assert response.status_code == 200
    assert not (upload_folder / SESSION_DIRNAME / upload_id).exists()
    assert authenticated_client.get(f"/admin/media/chunked/{upload_id}").status_code == 404


def test_stale_sessions_are_purged_on_init(authenticated_client, upload_folder):
    stale = upload_folder / SESSION_DIRNAME / "stale-session"
    stale.mkdir(parents=True)
    old = 25 * 3600
    os.utime(stale, (old, old))

    assert _start(authenticated_client, 1024).status_code == 201
    assert not stale.exists()


def test_in_progress_sessions_stay_out_of_the_library(authenticated_client, upload_folder):
    _start(authenticated_client, CHUNK_SIZE + 10)

    response = authenticated_client.get("/admin/media/items")

    assert response.status_code == 200
    assert response.get_json()["items"] == []


def test_other_category_roundtrip(authenticated_client, upload_folder):
    payload = b"\x7fELF" + os.urandom(1000)
    plan = _start(
        authenticated_client, len(payload), category="other", filename="tool.bin"
    ).get_json()
    upload_id = plan["upload_id"]
    authenticated_client.put(
        f"/admin/media/chunked/{upload_id}/0",
        data=payload,
        content_type="application/octet-stream",
    )

    response = authenticated_client.post(f"/admin/media/chunked/{upload_id}/complete")

    assert response.status_code == 201
    item = response.get_json()["item"]
    assert item["category"] == "other"
    assert item["name"].endswith(".attachment")
    assert (upload_folder / item["name"]).read_bytes() == payload


def test_chunked_cap_is_configured():
    assert CHUNKED_UPLOAD_MAX_SIZE == 1073741824


def test_save_path_moves_large_files_without_loading_them(authenticated_client, upload_folder):
    from app.storage import get_storage

    source = upload_folder / "source.bin"
    source.write_bytes(os.urandom(1024))

    assert get_storage().save_path("moved.bin", str(source)) == "moved.bin"
    assert (upload_folder / "moved.bin").is_file()
    assert not source.exists()
