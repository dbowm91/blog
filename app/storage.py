"""Storage abstraction layer for media files.

Supports local filesystem and S3-compatible storage backends.
Configure via STORAGE_BACKEND env var: "local" (default) or "s3".

For S3, set these env vars:
- STORAGE_BACKEND=s3
- S3_BUCKET (required)
- S3_REGION (default: us-east-1)
- S3_ENDPOINT (optional, for S3-compatible services)
- S3_ACCESS_KEY (required)
- S3_SECRET_KEY (required)
- S3_PUBLIC_URL (optional, for custom CDN URLs)

Known Limitations
-----------------
S3StorageBackend.exists() and list_files() do not differentiate between
"not found" and other errors. Both return False/empty list on any error,
making it impossible to distinguish network failures, permission errors,
or bucket issues from a simple404. This is a design limitation; fixing
would require an API change to return discriminated results (e.g.,
Result[T, StorageError]).
"""

from __future__ import annotations

import mimetypes
import os
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING, Any

# Optional botocore imports - only needed for S3 storage backend
try:
    from botocore.exceptions import ClientError
    from botocore.exceptions import BotoCoreError
except ImportError:
    # For type checking purposes when botocore is not installed
    if TYPE_CHECKING:
        from botocore.exceptions import ClientError
        from botocore.exceptions import BotoCoreError
    else:

        class ClientError(Exception):
            pass

        class BotoCoreError(Exception):
            pass


logger = logging.getLogger(__name__)


@dataclass
class StorageFileInfo:
    name: str
    size: int
    mtime: datetime | None
    url: str


STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")

_S3_BUCKET = os.environ.get("S3_BUCKET", "")
_S3_REGION = os.environ.get("S3_REGION", "us-east-1")
_S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")
_S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
_S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
_S3_PUBLIC_URL = os.environ.get("S3_PUBLIC_URL", "").rstrip("/")


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def save(self, filename: str, data: bytes) -> str:
        """Save data to storage, return the stored filename."""

    @abstractmethod
    def load(self, filename: str) -> Optional[bytes]:
        """Load data from storage, return bytes or None."""

    @abstractmethod
    def delete(self, filename: str) -> bool:
        """Delete a file from storage, return True on success."""

    @abstractmethod
    def exists(self, filename: str) -> bool:
        """Check if a file exists in storage."""

    @abstractmethod
    def url(self, filename: str) -> str:
        """Get the URL for a file."""

    @abstractmethod
    def list_files(self, prefix: str = "") -> list[str]:
        """List files with optional prefix filter."""

    @abstractmethod
    def list_file_info(self, prefix: str = "") -> list[StorageFileInfo]:
        """List files with metadata (size, mtime, URL)."""


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def save(self, filename: str, data: bytes) -> str:
        filepath = os.path.join(self.base_dir, filename)
        with open(filepath, "wb") as f:
            f.write(data)
        return filename

    def load(self, filename: str) -> Optional[bytes]:
        filepath = os.path.join(self.base_dir, filename)
        if not os.path.isfile(filepath):
            return None
        with open(filepath, "rb") as f:
            return f.read()

    def read_header(self, filename: str, length: int = 32) -> bytes:
        filepath = os.path.join(self.base_dir, filename)
        if not os.path.isfile(filepath):
            return b""
        with open(filepath, "rb") as f:
            return f.read(length)

    def delete(self, filename: str) -> bool:
        filepath = os.path.join(self.base_dir, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
            return True
        return False

    def exists(self, filename: str) -> bool:
        filepath = os.path.join(self.base_dir, filename)
        return os.path.isfile(filepath)

    def url(self, filename: str) -> str:
        return f"/static/uploads/{filename}"

    def list_files(self, prefix: str = "") -> list[str]:
        if not os.path.isdir(self.base_dir):
            return []
        files = []
        for entry in os.scandir(self.base_dir):
            if entry.is_file():
                if not prefix or entry.name.startswith(prefix):
                    files.append(entry.name)
        return sorted(files)

    def list_file_info(self, prefix: str = "") -> list[StorageFileInfo]:
        if not os.path.isdir(self.base_dir):
            return []
        files = []
        for entry in os.scandir(self.base_dir):
            if entry.is_file():
                if not prefix or entry.name.startswith(prefix):
                    try:
                        stat = entry.stat()
                        files.append(
                            StorageFileInfo(
                                name=entry.name,
                                size=stat.st_size,
                                mtime=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                                url=self.url(entry.name),
                            )
                        )
                    except OSError:
                        continue
        return sorted(
            files, key=lambda f: f.mtime or datetime.min.replace(tzinfo=timezone.utc), reverse=True
        )

    def path(self, filename: str) -> str:
        return os.path.join(self.base_dir, filename)


class S3StorageBackend(StorageBackend):
    """S3-compatible storage backend using boto3."""

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint: str = "",
        access_key: str = "",
        secret_key: str = "",
        public_url: str = "",
    ):
        self.bucket = bucket
        self.region = region
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.public_url = public_url
        self._client = None
        self._lock = threading.Lock()

    @property
    def client(self) -> Any:
        if self._client is None:
            with self._lock:
                if self._client is None:
                    import boto3

                    client_kwargs = {
                        "region_name": self.region,
                        "aws_access_key_id": self.access_key,
                        "aws_secret_access_key": self.secret_key,
                    }
                    if self.endpoint:
                        client_kwargs["endpoint_url"] = self.endpoint

                    self._client = boto3.client("s3", **client_kwargs)
        return self._client

    def save(self, filename: str, data: bytes) -> str:
        try:
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            params = {
                "Bucket": self.bucket,
                "Key": filename,
                "Body": data,
                "ContentType": content_type,
            }
            if filename.endswith(".attachment"):
                params["ContentType"] = "application/octet-stream"
                params["ContentDisposition"] = "attachment"
            self.client.put_object(**params)
            return filename
        except (ClientError, BotoCoreError) as e:
            logger.error("S3 save failed: %s", e)
            raise

    def read_header(self, filename: str, length: int = 32) -> bytes:
        try:
            response = self.client.get_object(
                Bucket=self.bucket, Key=filename, Range=f"bytes=0-{length - 1}"
            )
            body = response["Body"].read(length)
            return bytes(body) if body else b""
        except (ClientError, BotoCoreError):
            return b""

    def load(self, filename: str) -> Optional[bytes]:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=filename)
            body = response["Body"].read()
            return bytes(body) if body else None
        except (ClientError, BotoCoreError) as e:
            logger.error("S3 operation failed: %s", e)
            return None
        except (KeyboardInterrupt, SystemExit):
            raise

    def delete(self, filename: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=filename)
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error("S3 operation failed: %s", e)
            return False
        except (KeyboardInterrupt, SystemExit):
            raise

    def exists(self, filename: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=filename)
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error("S3 operation failed: %s", e)
            return False
        except (KeyboardInterrupt, SystemExit):
            raise

    def url(self, filename: str) -> str:
        if self.public_url:
            return f"{self.public_url}/{filename}"
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{filename}"

    def list_files(self, prefix: str = "") -> list[str]:
        try:
            kwargs = {"Bucket": self.bucket}
            if prefix:
                kwargs["Prefix"] = prefix
            response = self.client.list_objects_v2(**kwargs)
            contents = response.get("Contents", [])
            return sorted([obj["Key"] for obj in contents])
        except (ClientError, BotoCoreError) as e:
            logger.error("S3 operation failed: %s", e)
            return []
        except (KeyboardInterrupt, SystemExit):
            raise

    def list_file_info(self, prefix: str = "") -> list[StorageFileInfo]:
        try:
            kwargs = {"Bucket": self.bucket}
            if prefix:
                kwargs["Prefix"] = prefix
            contents = []
            while True:
                response = self.client.list_objects_v2(**kwargs)
                contents.extend(response.get("Contents", []))
                continuation = response.get("NextContinuationToken")
                if not response.get("IsTruncated") or not continuation:
                    break
                kwargs["ContinuationToken"] = continuation
            files = []
            for obj in contents:
                files.append(
                    StorageFileInfo(
                        name=obj["Key"],
                        size=obj["Size"],
                        mtime=obj.get("LastModified"),
                        url=self.url(obj["Key"]),
                    )
                )
            return sorted(
                files,
                key=lambda f: f.mtime or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
        except (ClientError, BotoCoreError) as e:
            logger.error("S3 operation failed: %s", e)
            return []
        except (KeyboardInterrupt, SystemExit):
            raise


def _storage_settings() -> dict[str, str]:
    """Resolve the storage settings.

    The typed configuration wins over the environment snapshot taken at
    import time, so ``[storage]`` in config.toml is not inert. The
    environment is still the fallback for callers outside an app context.
    """
    settings = {
        "backend": STORAGE_BACKEND,
        "s3_bucket": _S3_BUCKET,
        "s3_region": _S3_REGION,
        "s3_endpoint": _S3_ENDPOINT,
        "s3_access_key": _S3_ACCESS_KEY,
        "s3_secret_key": _S3_SECRET_KEY,
        "s3_public_url": _S3_PUBLIC_URL,
    }

    try:
        from flask import current_app, has_app_context

        if has_app_context():
            cfg = current_app.config.get("DEVLOG_CONFIG")
            storage = getattr(cfg, "storage", None) if cfg is not None else None
            if storage is not None:
                settings["backend"] = storage.backend or settings["backend"]
                settings["s3_bucket"] = storage.s3_bucket or settings["s3_bucket"]
                settings["s3_region"] = storage.s3_region or settings["s3_region"]
                settings["s3_endpoint"] = storage.s3_endpoint or settings["s3_endpoint"]
                settings["s3_access_key"] = storage.s3_access_key or settings["s3_access_key"]
                settings["s3_secret_key"] = storage.s3_secret_key or settings["s3_secret_key"]
                settings["s3_public_url"] = storage.s3_public_url or settings["s3_public_url"]
    except Exception:
        pass

    return settings


def _upload_folder() -> str:
    """Resolve the directory that holds uploaded media."""
    default = os.path.join(os.path.dirname(__file__), "static", "uploads")

    try:
        from flask import current_app, has_app_context

        if has_app_context():
            configured = current_app.config.get("UPLOAD_FOLDER")
            if configured:
                return str(configured)
    except Exception:
        pass

    return os.environ.get("UPLOAD_FOLDER", default)


def get_storage_backend() -> StorageBackend:
    """Factory function to get the configured storage backend."""
    settings = _storage_settings()

    if settings["backend"] == "s3":
        missing = []
        if not settings["s3_bucket"]:
            missing.append("S3_BUCKET")
        if not settings["s3_access_key"]:
            missing.append("S3_ACCESS_KEY")
        if not settings["s3_secret_key"]:
            missing.append("S3_SECRET_KEY")
        if missing:
            logger.warning(
                "STORAGE_BACKEND=s3 but missing required config: %s. "
                "Falling back to local storage. Set these env vars to enable S3.",
                ", ".join(missing),
            )
            return LocalStorageBackend(_upload_folder())
        return S3StorageBackend(
            bucket=settings["s3_bucket"],
            region=settings["s3_region"],
            endpoint=settings["s3_endpoint"],
            access_key=settings["s3_access_key"],
            secret_key=settings["s3_secret_key"],
            public_url=settings["s3_public_url"],
        )

    return LocalStorageBackend(_upload_folder())


_storage: Optional[StorageBackend] = None
_storage_lock = threading.Lock()


def init_storage() -> StorageBackend:
    """Bind the storage backend to the application's configuration.

    The backend is built inside the application context, so the local backend
    resolves the configured upload folder and the S3 settings come from the
    application configuration. Built outside that context it fell back to the
    folder in the source tree, and every upload of a deployment that keeps its
    media outside the installation directory landed there.

    A process serves one application, so the first application binds the
    backend and later ones keep it.
    """
    global _storage
    if _storage is None:
        with _storage_lock:
            if _storage is None:
                _storage = get_storage_backend()
    return _storage


def get_storage() -> StorageBackend:
    """Get the storage backend (singleton)."""
    global _storage
    if _storage is None:
        with _storage_lock:
            if _storage is None:
                _storage = get_storage_backend()
    return _storage


def storage_delete_file(filename: str) -> bool:
    """Delete a file from storage, returning True on success."""
    storage = get_storage()
    return storage.delete(filename)


def _delete_existing_variants(storage: StorageBackend, filename: str) -> None:
    """Delete existing variants for a file before uploading new version.

    Handles cleanup of: 400_, 800_, 1200_ prefixes, .webp, .avif suffixes.
    """
    if isinstance(storage, LocalStorageBackend):
        upload_folder = storage.base_dir
        name, ext = os.path.splitext(filename)
        variant_patterns = [
            filename,  # Original
            f"400_{filename}",
            f"800_{filename}",
            f"1200_{filename}",
            f"{name}.webp",
            f"{name}.avif",
        ]
        for variant in variant_patterns:
            variant_path = os.path.join(upload_folder, variant)
            if os.path.isfile(variant_path):
                try:
                    os.remove(variant_path)
                    logger.debug("Deleted variant: %s", variant)
                except OSError as e:
                    logger.warning("Failed to delete variant %s: %s", variant, e)
    elif isinstance(storage, S3StorageBackend):
        name, ext = os.path.splitext(filename)
        prefixes_to_delete = [
            filename,
            f"400_{filename}",
            f"800_{filename}",
            f"1200_{filename}",
            f"{name}.webp",
            f"{name}.avif",
        ]
        for prefix in prefixes_to_delete:
            try:
                response = storage.client.list_objects_v2(Bucket=storage.bucket, Prefix=prefix)
                for obj in response.get("Contents", []):
                    storage.client.delete_object(Bucket=storage.bucket, Key=obj["Key"])
                    logger.debug("Deleted S3 object: %s", obj["Key"])
            except (ClientError, BotoCoreError) as e:
                logger.warning("Failed to delete S3 variants with prefix %s: %s", prefix, e)


def upload_with_processing(
    filename: str, file_content: bytes, generate_variants: bool = True
) -> tuple[str, None] | tuple[None, str]:
    """Save an image file and optionally queue async variant generation.

    For local storage: saves directly to upload folder.
    For S3 storage: saves to temp, uploads to S3.
    Variant generation is queued as a Celery task if generate_variants is True.

    Args:
        filename: The filename to store as
        file_content: The raw file bytes
        generate_variants: Whether to queue async responsive variant generation

    Returns:
        (filename, None) on success, (None, error_message) on failure
    """
    storage = get_storage()

    _delete_existing_variants(storage, filename)

    if isinstance(storage, LocalStorageBackend):
        filepath = os.path.join(storage.base_dir, filename)
        with open(filepath, "wb") as f:
            f.write(file_content)

    elif isinstance(storage, S3StorageBackend):
        storage.save(filename, file_content)

    else:
        return None, "Unknown storage backend"

    if generate_variants:
        try:
            from app.tasks import generate_image_variants

            generate_image_variants.delay(filename)
        except Exception:
            logger.debug("Celery unavailable, skipping async variant generation for %s", filename)

    return filename, None


def _generate_responsive_variants_local(filepath: str) -> None:
    """Deprecated: Variant generation is now handled by Celery task generate_image_variants."""
    from app.tasks import generate_image_variants
    import os

    filename = os.path.basename(filepath)
    generate_image_variants.delay(filename)
