"""Bounded, fixed-host GitHub API reads for project integrations."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from app import http_client

GITHUB_API_ROOT = "https://api.github.com"
GITHUB_MEDIA_TYPE = "application/vnd.github+json"
GITHUB_API_VERSION = "2022-11-28"
DEFAULT_CONNECT_TIMEOUT = 3.05
DEFAULT_READ_TIMEOUT = 10.0
DEFAULT_RESPONSE_LIMIT = 2 * 1024 * 1024
DEFAULT_MAX_PATH_SEGMENTS = 64
MAX_RETRIES = 2
OWNER_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")
REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,98}[A-Za-z0-9]?\Z")


def validate_repository_identity(owner: str, repository: str) -> tuple[str, str]:
    if not OWNER_PATTERN.fullmatch(owner) or not REPOSITORY_PATTERN.fullmatch(repository):
        raise ValueError("GitHub repository identity is invalid")
    if repository in {".", ".."} or ".." in repository:
        raise ValueError("GitHub repository identity is invalid")
    return owner, repository


class GitHubApiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
        rate_limit_reset: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        self.rate_limit_reset = rate_limit_reset


class GitHubRequestError(GitHubApiError, ValueError):
    """Raised when a request is rejected before it reaches the network.

    It is both an API failure and a value error so a caller that validates the
    request itself sees the same exception class as a caller that awaits the
    upstream response.
    """


@dataclass(frozen=True)
class GitHubJsonResponse:
    data: Any | None
    etag: str | None
    not_modified: bool
    rate_limit_remaining: int | None
    rate_limit_reset: int | None


class GitHubApiClient:
    def __init__(
        self,
        *,
        session: http_client.Client | None = None,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
        max_response_bytes: int = DEFAULT_RESPONSE_LIMIT,
        max_path_segments: int = DEFAULT_MAX_PATH_SEGMENTS,
        max_retries: int = MAX_RETRIES,
        retry_base_seconds: float = 0.1,
        sleep=time.sleep,
    ) -> None:
        if connect_timeout <= 0 or read_timeout <= 0:
            raise ValueError("GitHub timeouts must be positive")
        if max_response_bytes <= 0:
            raise ValueError("GitHub response limit must be positive")
        if max_path_segments <= 0:
            raise ValueError("GitHub path segment limit must be positive")
        if max_retries < 0 or max_retries > MAX_RETRIES:
            raise ValueError("GitHub retries must be between zero and two")
        self._owns_session = session is None
        self.session = session or http_client.Client()
        self.timeout = (connect_timeout, read_timeout)
        self.max_response_bytes = max_response_bytes
        self.max_path_segments = max_path_segments
        self.max_retries = max_retries
        self.retry_base_seconds = max(0.0, retry_base_seconds)
        self.sleep = sleep

    def close(self) -> None:
        if self._owns_session:
            self.session.close()

    def get_json(
        self,
        path_segments: tuple[str, ...] | list[str],
        *,
        params: dict[str, str | int | bool] | None = None,
        etag: str | None = None,
    ) -> GitHubJsonResponse:
        path = self._path(path_segments)
        headers = {
            "Accept": GITHUB_MEDIA_TYPE,
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": "DevLog-Project-Integration",
        }
        if etag:
            headers["If-None-Match"] = etag

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    f"{GITHUB_API_ROOT}/{path}",
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=False,
                    stream=True,
                )
            except http_client.RequestException as exc:
                if attempt < self.max_retries:
                    self.sleep(self.retry_base_seconds * (2**attempt))
                    continue
                raise GitHubApiError("GitHub API request failed") from exc

            try:
                status = int(response.status_code)
                if status == 304:
                    return self._result(response, None, not_modified=True)
                if status in {301, 302, 303, 307, 308}:
                    raise GitHubApiError(
                        "GitHub API redirects are not permitted", status_code=status
                    )
                if status in {502, 503, 504} and attempt < self.max_retries:
                    self.sleep(self.retry_base_seconds * (2**attempt))
                    continue
                if status == 429 or (
                    status == 403
                    and (
                        response.headers.get("X-RateLimit-Remaining") == "0"
                        or response.headers.get("Retry-After") is not None
                    )
                ):
                    raise GitHubApiError(
                        "GitHub API rate limit reached",
                        status_code=status,
                        retry_after_seconds=self._retry_after(response.headers.get("Retry-After")),
                        rate_limit_reset=self._integer_header(
                            response.headers, "X-RateLimit-Reset"
                        ),
                    )
                if status < 200 or status >= 300:
                    raise GitHubApiError(
                        "GitHub API returned an unsuccessful response", status_code=status
                    )

                content_type = (
                    response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                )
                if content_type != "application/json" and not content_type.endswith("+json"):
                    raise GitHubApiError("GitHub API response was not JSON", status_code=status)
                body = self._read_limited(response)
                try:
                    data = json.loads(body)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise GitHubApiError(
                        "GitHub API returned invalid JSON", status_code=status
                    ) from exc
                return self._result(response, data, not_modified=False)
            finally:
                response.close()

        raise GitHubApiError("GitHub API request failed after bounded retries")

    def _path(self, path_segments: tuple[str, ...] | list[str]) -> str:
        if not path_segments or len(path_segments) > self.max_path_segments:
            raise GitHubRequestError("GitHub API path is invalid")
        encoded: list[str] = []
        for segment in path_segments:
            if (
                not isinstance(segment, str)
                or not segment
                or segment in {".", ".."}
                or len(segment) > 256
                or any(ord(char) < 32 or char in "\\?#" for char in segment)
            ):
                raise GitHubRequestError("GitHub API path segment is invalid")
            encoded.append(quote(segment, safe=""))
        return "/".join(encoded)

    def _read_limited(self, response: http_client.Response) -> bytes:
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > self.max_response_bytes:
                    raise GitHubApiError("GitHub API response exceeded the configured size limit")
            except ValueError as exc:
                raise GitHubApiError("GitHub API response had an invalid content length") from exc

        chunks: list[bytes] = []
        total = 0
        try:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > self.max_response_bytes:
                    raise GitHubApiError("GitHub API response exceeded the configured size limit")
                chunks.append(chunk)
        except http_client.RequestException as exc:
            raise GitHubApiError("GitHub API response could not be read") from exc
        return b"".join(chunks)

    @staticmethod
    def _result(
        response: http_client.Response,
        data: Any | None,
        *,
        not_modified: bool,
    ) -> GitHubJsonResponse:
        return GitHubJsonResponse(
            data=data,
            etag=response.headers.get("ETag"),
            not_modified=not_modified,
            rate_limit_remaining=GitHubApiClient._integer_header(
                response.headers, "X-RateLimit-Remaining"
            ),
            rate_limit_reset=GitHubApiClient._integer_header(response.headers, "X-RateLimit-Reset"),
        )

    @staticmethod
    def _integer_header(headers: Any, name: str) -> int | None:
        value = headers.get(name)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _retry_after(value: str | None) -> float | None:
        if value is None:
            return None
        try:
            seconds = float(value)
        except ValueError:
            return None
        return seconds if seconds >= 0 else None
