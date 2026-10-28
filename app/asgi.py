"""ASGI entry point for production servers.

``run.py`` lives at the repository root, so it is only importable from a
source checkout. An installed release contains the virtualenv alone, so the
ASGI application is exposed here, inside the package, and is importable from
``site-packages``:

    granian --interface asgi --workers 4 --host 127.0.0.1 --port 5000 app.asgi:asgi_app
"""

from __future__ import annotations

from asgiref.wsgi import WsgiToAsgi

from app import create_app

app = create_app()
asgi_app = WsgiToAsgi(app)

__all__ = ["app", "asgi_app"]
