"""Coverage for app/storage.py.

Targets the S3 backend, the local listing helpers, the variant cleanup and the
upload path, none of which the happy-path suite reaches.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
import types
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

import app.storage as storage_module
from app.storage import LocalStorageBackend, S3StorageBackend


def _fake_boto(monkeypatch):
    """Install stub botocore/boto3 modules and return them."""
    exceptions = types.ModuleType("botocore.exceptions")

    class ClientError(Exception):
        def __init__(self, response=None, operation_name=None):
            super().__init__(str(response))
            self.response = response
            self.operation_name = operation_name

    class BotoCoreError(Exception):
        pass

    exceptions.ClientError = ClientError
    exceptions.BotoCoreError = BotoCoreError

    botocore = types.ModuleType("botocore")
    botocore.exceptions = exceptions

    boto3 = types.ModuleType("boto3")
    boto3.client = MagicMock(name="boto3.client")

    monkeypatch.setitem(sys.modules, "botocore", botocore)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", exceptions)
    monkeypatch.setitem(sys.modules, "boto3", boto3)

    return types.SimpleNamespace(
        boto3=boto3,
        botocore=botocore,
        exceptions=exceptions,
        ClientError=ClientError,
        BotoCoreError=BotoCoreError,
    )


def _s3_backend(**kwargs):
    options = {
        "bucket": "blog-bucket",
        "region": "eu-west-1",
        "endpoint": "",
        "access_key": "acctest",
        "secret_key": "sectest",
        "public_url": "",
    }
    options.update(kwargs)
    return S3StorageBackend(**options)


def _s3_with_client(**kwargs):
    backend = _s3_backend(**kwargs)
    backend._client = MagicMock(name="s3-client")
    backend._client.list_objects_v2.return_value = {"Contents": []}
    return backend


def test_module_uses_botocore_errors_when_the_package_is_available(monkeypatch):
    fake = _fake_boto(monkeypatch)

    spec = importlib.util.spec_from_file_location("storage_botocore_probe", storage_module.__file__)
    probe = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "storage_botocore_probe", probe)
    spec.loader.exec_module(probe)

    assert probe.ClientError is fake.ClientError
    assert probe.BotoCoreError is fake.BotoCoreError


def test_s3_client_is_built_once_with_the_configured_endpoint(monkeypatch):
    fake = _fake_boto(monkeypatch)
    backend = _s3_backend(endpoint="https://minio.example")

    client = backend.client

    fake.boto3.client.assert_called_once_with(
        "s3",
        region_name="eu-west-1",
        aws_access_key_id="acctest",
        aws_secret_access_key="sectest",
        endpoint_url="https://minio.example",
    )
    assert backend.client is client
    assert fake.boto3.client.call_count == 1


def test_s3_client_without_endpoint_omits_the_endpoint_url(monkeypatch):
    fake = _fake_boto(monkeypatch)
    backend = _s3_backend()

    backend.client

    fake.boto3.client.assert_called_once_with(
        "s3",
        region_name="eu-west-1",
        aws_access_key_id="acctest",
        aws_secret_access_key="sectest",
    )


def test_s3_save_uploads_the_object():
    backend = _s3_with_client()

    assert backend.save("photo.jpg", b"bytes") == "photo.jpg"
    backend._client.put_object.assert_called_once_with(
        Bucket="blog-bucket", Key="photo.jpg", Body=b"bytes"
    )


def test_s3_save_reraises_client_errors():
    backend = _s3_with_client()
    backend._client.put_object.side_effect = storage_module.ClientError({"Error": "denied"})

    with pytest.raises(storage_module.ClientError):
        backend.save("photo.jpg", b"bytes")


def test_s3_load_returns_the_object_body():
    backend = _s3_with_client()
    backend._client.get_object.return_value = {"Body": MagicMock(read=lambda: b"payload")}

    assert backend.load("photo.jpg") == b"payload"


def test_s3_load_returns_none_for_an_empty_body():
    backend = _s3_with_client()
    backend._client.get_object.return_value = {"Body": MagicMock(read=lambda: b"")}

    assert backend.load("photo.jpg") is None


def test_s3_load_returns_none_on_client_error():
    backend = _s3_with_client()
    backend._client.get_object.side_effect = storage_module.ClientError({"Error": "missing"})

    assert backend.load("photo.jpg") is None


def test_s3_load_does_not_swallow_interrupts():
    backend = _s3_with_client()
    backend._client.get_object.side_effect = KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        backend.load("photo.jpg")


def test_s3_delete_removes_the_object():
    backend = _s3_with_client()

    assert backend.delete("photo.jpg") is True
    backend._client.delete_object.assert_called_once_with(Bucket="blog-bucket", Key="photo.jpg")


def test_s3_delete_returns_false_on_client_error():
    backend = _s3_with_client()
    backend._client.delete_object.side_effect = storage_module.BotoCoreError("boom")

    assert backend.delete("photo.jpg") is False


def test_s3_delete_does_not_swallow_interrupts():
    backend = _s3_with_client()
    backend._client.delete_object.side_effect = KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        backend.delete("photo.jpg")


def test_s3_exists_is_true_for_a_present_object():
    backend = _s3_with_client()

    assert backend.exists("photo.jpg") is True
    backend._client.head_object.assert_called_once_with(Bucket="blog-bucket", Key="photo.jpg")


def test_s3_exists_is_false_on_client_error():
    backend = _s3_with_client()
    backend._client.head_object.side_effect = storage_module.ClientError({"Error": "missing"})

    assert backend.exists("photo.jpg") is False


def test_s3_exists_does_not_swallow_interrupts():
    backend = _s3_with_client()
    backend._client.head_object.side_effect = KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        backend.exists("photo.jpg")


def test_s3_url_uses_the_public_url_when_configured():
    backend = _s3_backend(public_url="https://cdn.example")

    assert backend.url("photo.jpg") == "https://cdn.example/photo.jpg"


def test_s3_url_falls_back_to_the_bucket_endpoint():
    backend = _s3_backend()

    assert backend.url("photo.jpg") == "https://blog-bucket.s3.eu-west-1.amazonaws.com/photo.jpg"


def test_s3_list_files_sorts_the_keys_and_filters_by_prefix():
    backend = _s3_with_client()
    backend._client.list_objects_v2.return_value = {
        "Contents": [{"Key": "b.txt"}, {"Key": "a.txt"}]
    }

    assert backend.list_files("a") == ["a.txt", "b.txt"]
    backend._client.list_objects_v2.assert_called_once_with(Bucket="blog-bucket", Prefix="a")


def test_s3_list_files_without_a_prefix_lists_every_object():
    backend = _s3_with_client()
    backend._client.list_objects_v2.return_value = {"Contents": [{"Key": "a.txt"}]}

    assert backend.list_files() == ["a.txt"]
    backend._client.list_objects_v2.assert_called_once_with(Bucket="blog-bucket")


def test_s3_list_files_returns_empty_when_the_bucket_has_no_objects():
    backend = _s3_with_client()
    backend._client.list_objects_v2.return_value = {}

    assert backend.list_files() == []


def test_s3_list_files_returns_empty_on_client_error():
    backend = _s3_with_client()
    backend._client.list_objects_v2.side_effect = storage_module.BotoCoreError("boom")

    assert backend.list_files() == []


def test_s3_list_files_does_not_swallow_interrupts():
    backend = _s3_with_client()
    backend._client.list_objects_v2.side_effect = KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        backend.list_files()


def test_s3_list_file_info_returns_metadata_newest_first():
    backend = _s3_with_client(public_url="https://cdn.example")
    backend._client.list_objects_v2.return_value = {
        "Contents": [
            {
                "Key": "old.jpg",
                "Size": 10,
                "LastModified": datetime(2024, 1, 1, tzinfo=timezone.utc),
            },
            {
                "Key": "new.jpg",
                "Size": 20,
                "LastModified": datetime(2024, 6, 1, tzinfo=timezone.utc),
            },
        ]
    }

    infos = backend.list_file_info()

    assert [info.name for info in infos] == ["new.jpg", "old.jpg"]
    assert infos[0].size == 20
    assert infos[0].url == "https://cdn.example/new.jpg"
    assert infos[0].mtime == datetime(2024, 6, 1, tzinfo=timezone.utc)


def test_s3_list_file_info_handles_objects_without_a_timestamp():
    backend = _s3_with_client()
    backend._client.list_objects_v2.return_value = {"Contents": [{"Key": "a.jpg", "Size": 1}]}

    infos = backend.list_file_info()

    assert len(infos) == 1
    assert infos[0].mtime is None
    assert infos[0].size == 1


def test_s3_list_file_info_returns_empty_on_client_error():
    backend = _s3_with_client()
    backend._client.list_objects_v2.side_effect = storage_module.ClientError({"Error": "denied"})

    assert backend.list_file_info() == []


def test_s3_list_file_info_does_not_swallow_interrupts():
    backend = _s3_with_client()
    backend._client.list_objects_v2.side_effect = KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        backend.list_file_info()


def test_local_listing_returns_empty_when_the_folder_is_gone(tmp_path):
    base = tmp_path / "uploads"
    backend = LocalStorageBackend(str(base))
    base.rmdir()

    assert backend.list_files() == []
    assert backend.list_file_info() == []


def test_local_list_file_info_skips_entries_that_cannot_be_statted(tmp_path):
    backend = LocalStorageBackend(str(tmp_path))

    class BrokenEntry:
        def is_file(self):
            return True

        def stat(self):
            raise OSError("vanished")

    with patch("app.storage.os.scandir", return_value=[BrokenEntry()]):
        assert backend.list_file_info() == []


def test_local_path_points_at_the_file(tmp_path):
    backend = LocalStorageBackend(str(tmp_path))

    assert backend.path("photo.jpg") == os.path.join(str(tmp_path), "photo.jpg")


def test_storage_settings_survive_a_broken_flask_context():
    with patch("flask.has_app_context", side_effect=RuntimeError("no context")):
        settings = storage_module._storage_settings()

    assert settings["backend"] == storage_module.STORAGE_BACKEND
    assert settings["s3_bucket"] == storage_module._S3_BUCKET


def test_upload_folder_survives_a_broken_flask_context(monkeypatch):
    monkeypatch.setenv("UPLOAD_FOLDER", "/srv/uploads")

    with patch("flask.has_app_context", side_effect=RuntimeError("no context")):
        folder = storage_module._upload_folder()

    assert folder == "/srv/uploads"


def test_get_storage_backend_builds_the_s3_backend(monkeypatch):
    monkeypatch.setattr(
        storage_module,
        "_storage_settings",
        lambda: {
            "backend": "s3",
            "s3_bucket": "blog-bucket",
            "s3_region": "eu-west-1",
            "s3_endpoint": "https://minio.example",
            "s3_access_key": "access",
            "s3_secret_key": "secret",
            "s3_public_url": "https://cdn.example",
        },
    )

    backend = storage_module.get_storage_backend()

    assert isinstance(backend, S3StorageBackend)
    assert backend.bucket == "blog-bucket"
    assert backend.endpoint == "https://minio.example"
    assert backend.public_url == "https://cdn.example"


def test_upload_with_processing_stores_the_file_in_s3(monkeypatch):
    backend = _s3_with_client()
    monkeypatch.setattr(storage_module, "get_storage", lambda: backend)

    name, error = storage_module.upload_with_processing(
        "photo.jpg", b"bytes", generate_variants=False
    )

    assert (name, error) == ("photo.jpg", None)
    backend._client.put_object.assert_called_once_with(
        Bucket="blog-bucket", Key="photo.jpg", Body=b"bytes"
    )


def test_upload_with_processing_rejects_an_unknown_backend(monkeypatch):
    class UnknownBackend:
        pass

    monkeypatch.setattr(storage_module, "get_storage", lambda: UnknownBackend())

    name, error = storage_module.upload_with_processing(
        "photo.jpg", b"bytes", generate_variants=False
    )

    assert name is None
    assert error == "Unknown storage backend"


def test_upload_with_processing_survives_a_missing_broker(monkeypatch, tmp_path):
    backend = LocalStorageBackend(str(tmp_path))
    monkeypatch.setattr(storage_module, "get_storage", lambda: backend)

    with patch("app.tasks.generate_image_variants") as mock_task:
        mock_task.delay.side_effect = RuntimeError("no broker")
        name, error = storage_module.upload_with_processing("photo.jpg", b"bytes")

    assert (name, error) == ("photo.jpg", None)
    assert (tmp_path / "photo.jpg").read_bytes() == b"bytes"


def test_delete_existing_variants_removes_every_local_variant(tmp_path):
    backend = LocalStorageBackend(str(tmp_path))
    names = (
        "photo.jpg",
        "400_photo.jpg",
        "800_photo.jpg",
        "1200_photo.jpg",
        "photo.webp",
        "photo.avif",
    )
    for name in names:
        (tmp_path / name).write_bytes(b"x")

    storage_module._delete_existing_variants(backend, "photo.jpg")

    assert list(tmp_path.iterdir()) == []


def test_delete_existing_variants_warns_when_a_local_variant_cannot_be_removed(tmp_path, caplog):
    backend = LocalStorageBackend(str(tmp_path))
    (tmp_path / "photo.jpg").write_bytes(b"x")

    with caplog.at_level(logging.WARNING):
        with patch("app.storage.os.remove", side_effect=OSError("busy")):
            storage_module._delete_existing_variants(backend, "photo.jpg")

    assert (tmp_path / "photo.jpg").exists()
    assert "Failed to delete variant" in caplog.text


def test_delete_existing_variants_removes_s3_objects():
    backend = _s3_with_client()

    def _listing(Bucket, Prefix):
        if Prefix == "photo.jpg":
            return {"Contents": [{"Key": "photo.jpg"}]}
        return {"Contents": []}

    backend._client.list_objects_v2.side_effect = _listing

    storage_module._delete_existing_variants(backend, "photo.jpg")

    backend._client.delete_object.assert_called_once_with(Bucket="blog-bucket", Key="photo.jpg")


def test_delete_existing_variants_warns_when_the_s3_listing_fails(caplog):
    backend = _s3_with_client()
    backend._client.list_objects_v2.side_effect = storage_module.ClientError({"Error": "denied"})

    with caplog.at_level(logging.WARNING):
        storage_module._delete_existing_variants(backend, "photo.jpg")

    assert "Failed to delete S3 variants" in caplog.text
    backend._client.delete_object.assert_not_called()


def test_generate_responsive_variants_local_queues_the_task():
    with patch("app.tasks.generate_image_variants") as mock_task:
        storage_module._generate_responsive_variants_local("/var/uploads/photo.jpg")

    mock_task.delay.assert_called_once_with("photo.jpg")
