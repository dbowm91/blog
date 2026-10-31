import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import Mock

import pytest

from app import http_client


def test_client_maps_timeout_redirect_and_stream_options(monkeypatch):
    native_client = Mock()
    native_response = Mock()
    native_response.status_code = 200
    native_response.iter_bytes.return_value = iter([b"body"])
    native_client.stream.return_value = native_response
    monkeypatch.setattr(http_client.eggfetch, "Client", lambda **kwargs: native_client)
    client = http_client.Client()

    response = client.get(
        "https://example.com",
        timeout=(3.0, 10.0),
        allow_redirects=False,
        stream=True,
    )

    native_client.stream.assert_called_once()
    call = native_client.stream.call_args
    assert call.args == ("GET", "https://example.com")
    assert call.kwargs["follow_redirects"] is False
    assert call.kwargs["timeout"].connect == 3.0
    assert call.kwargs["timeout"].read == 10.0
    assert response.status_code == 200
    assert list(response.iter_content(chunk_size=4)) == [b"body"]
    response.close()
    native_response.close.assert_called_once()
    client.close()
    native_client.close.assert_called_once()


def test_one_shot_stream_keeps_client_open_until_response_close(monkeypatch):
    native_client = Mock()
    native_response = Mock()
    native_response.status_code = 201
    native_client.stream.return_value = native_response
    monkeypatch.setattr(http_client.eggfetch, "Client", lambda **kwargs: native_client)

    response = http_client.post("https://example.com", stream=True, allow_redirects=False)

    native_client.stream.assert_called_once()
    assert native_client.close.call_count == 0
    assert response.status_code == 201
    response.close()
    native_response.close.assert_called_once()
    native_client.close.assert_called_once()


def test_one_shot_buffered_request_closes_client(monkeypatch):
    native_client = Mock()
    native_response = Mock()
    native_response.status_code = 201
    native_client.request.return_value = native_response
    monkeypatch.setattr(http_client.eggfetch, "Client", lambda **kwargs: native_client)

    response = http_client.post("https://example.com", json={"ok": True})

    native_client.request.assert_called_once()
    assert native_client.close.call_count == 1
    assert response.status_code == 201


def test_failed_one_shot_request_closes_client(monkeypatch):
    native_client = Mock()
    native_client.request.side_effect = http_client.RequestException("failed")
    monkeypatch.setattr(http_client.eggfetch, "Client", lambda **kwargs: native_client)

    with pytest.raises(http_client.RequestException, match="failed"):
        http_client.post("https://example.com")

    native_client.close.assert_called_once()


def test_client_sends_json_and_does_not_follow_redirects():
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append((self.path, body))
            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", "/redirect-target")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        response = http_client.post(
            f"{base_url}/webhook",
            json={"connected": True},
            timeout=(1.0, 1.0),
            allow_redirects=False,
        )
        assert response.status_code == 202
        response.close()

        redirect = http_client.get(
            f"{base_url}/redirect",
            timeout=(1.0, 1.0),
            allow_redirects=False,
        )
        assert redirect.status_code == 302
        redirect.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()

    assert received == [("/webhook", json.dumps({"connected": True}).encode())]
