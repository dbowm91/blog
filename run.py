from asgiref.wsgi import WsgiToAsgi
from app import create_app
from app.config import SERVER_HOST, SERVER_PORT, DEBUG

app = create_app()
asgi_app = WsgiToAsgi(app)

if __name__ == "__main__":
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG)
