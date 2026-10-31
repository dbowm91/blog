"""Application HTTP transport backed by eggfetch."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import eggfetch

RequestException = eggfetch.EggfetchError
TimeoutException = eggfetch.TimeoutException


def _timeout(
    value: float | tuple[float, float] | eggfetch.Timeout | None,
) -> float | eggfetch.Timeout | None:
    if isinstance(value, tuple):
        if len(value) != 2:
            raise ValueError("HTTP timeout tuple must contain connect and read values")
        return eggfetch.Timeout(connect=value[0], read=value[1])
    return value


class Response:
    def __init__(self, response: Any, client: eggfetch.Client | None = None) -> None:
        self._response = response
        self._client = client

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def headers(self) -> Any:
        return self._response.headers

    def iter_content(self, chunk_size: int = 8192) -> Iterator[bytes]:
        return self._response.iter_bytes(chunk_size=chunk_size)

    def close(self) -> None:
        try:
            self._response.close()
        finally:
            if self._client is not None:
                self._client.close()


class Client:
    def __init__(self) -> None:
        self._client = eggfetch.Client(follow_redirects=True)

    def get(self, url: str, **kwargs: Any) -> Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Response:
        return self.request("POST", url, **kwargs)

    def request(self, method: str, url: str, **kwargs: Any) -> Response:
        stream = kwargs.pop("stream", False)
        timeout = _timeout(kwargs.pop("timeout", None))
        allow_redirects = kwargs.pop("allow_redirects", None)
        options = {**kwargs, "timeout": timeout, "follow_redirects": allow_redirects}
        response = (
            self._client.stream(method, url, **options)
            if stream
            else self._client.request(method, url, **options)
        )
        return Response(response)

    def close(self) -> None:
        self._client.close()


def _request(method: str, url: str, **kwargs: Any) -> Response:
    client = eggfetch.Client(follow_redirects=True)
    stream = kwargs.pop("stream", False)
    timeout = _timeout(kwargs.pop("timeout", None))
    allow_redirects = kwargs.pop("allow_redirects", None)
    options = {**kwargs, "timeout": timeout, "follow_redirects": allow_redirects}
    try:
        if stream:
            return Response(client.stream(method, url, **options), client)
        response = client.request(method, url, **options)
    except BaseException:
        client.close()
        raise
    client.close()
    return Response(response)


def post(url: str, **kwargs: Any) -> Response:
    return _request("POST", url, **kwargs)


def get(url: str, **kwargs: Any) -> Response:
    return _request("GET", url, **kwargs)
