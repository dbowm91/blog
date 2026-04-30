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
"""

from __future__ import annotations

import os
import logging
import threading
from abc import ABC, abstractmethod
from typing import Optional

# Optional botocore imports - only needed for S3 storage backend
try:
    from botocore.exceptions import ClientError as _ClientError
    from botocore.exceptions import BotoCoreError as _BotoCoreError
    ClientError = _ClientError
    BotoCoreError = _BotoCoreError
except ImportError:
    # For type checking purposes when botocore is not installed
    class ClientError(Exception):
        pass
    class BotoCoreError(Exception):
        pass

logger = logging.getLogger(__name__)

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

    def path(self, filename: str) -> str:
        """Get local path for a file (only valid for LocalStorageBackend)."""
        raise NotImplementedError("path() is only available on LocalStorageBackend")


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
    def client(self):
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
        self.client.put_object(Bucket=self.bucket, Key=filename, Body=data)
        return filename

    def load(self, filename: str) -> Optional[bytes]:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=filename)
            return response["Body"].read()
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


def get_storage_backend() -> StorageBackend:
    """Factory function to get the configured storage backend."""
    if STORAGE_BACKEND == "s3":
        if not all([_S3_BUCKET, _S3_ACCESS_KEY, _S3_SECRET_KEY]):
            logger.warning(
                "S3 storage backend configured but missing credentials. "
                "Falling back to local storage."
            )
            upload_folder = os.environ.get(
                "UPLOAD_FOLDER",
                os.path.join(os.path.dirname(__file__), "static", "uploads"),
            )
            return LocalStorageBackend(upload_folder)
        return S3StorageBackend(
            bucket=_S3_BUCKET,
            region=_S3_REGION,
            endpoint=_S3_ENDPOINT,
            access_key=_S3_ACCESS_KEY,
            secret_key=_S3_SECRET_KEY,
            public_url=_S3_PUBLIC_URL,
        )

    upload_folder = os.environ.get(
        "UPLOAD_FOLDER",
        os.path.join(os.path.dirname(__file__), "static", "uploads"),
    )
    return LocalStorageBackend(upload_folder)


_storage: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """Get the global storage instance (singleton)."""
    global _storage
    if _storage is None:
        _storage = get_storage_backend()
    return _storage


def init_storage(base_dir: str) -> StorageBackend:
    """Initialize storage with the given base directory for local backend."""
    global _storage
    _storage = LocalStorageBackend(base_dir)
    return _storage


def storage_delete_file(filename: str) -> bool:
    """Delete a file from storage, returning True on success."""
    storage = get_storage()
    return storage.delete(filename)


def upload_with_processing(filename: str, file_content: bytes, generate_variants: bool = True) -> tuple[str, None] | tuple[None, str]:
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

    if isinstance(storage, LocalStorageBackend):
        upload_folder = os.environ.get(
            "UPLOAD_FOLDER",
            os.path.join(os.path.dirname(__file__), "static", "uploads"),
        )
        filepath = os.path.join(upload_folder, filename)
        with open(filepath, "wb") as f:
            f.write(file_content)

    elif isinstance(storage, S3StorageBackend):
        storage.save(filename, file_content)

    else:
        return None, "Unknown storage backend"

    if generate_variants:
        from app.tasks import generate_image_variants
        generate_image_variants.delay(filename)

    return filename, None


def _generate_responsive_variants_local(filepath: str):
    """Deprecated: Variant generation is now handled by Celery task generate_image_variants."""
    from app.tasks import generate_image_variants
    import os
    filename = os.path.basename(filepath)
    generate_image_variants.delay(filename)
