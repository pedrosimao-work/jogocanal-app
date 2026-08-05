from a2wsgi import ASGIMiddleware  # Import the adapter that exposes an ASGI application through a WSGI callable

from app.main import app  # Import the real FastAPI application from the application package


application = ASGIMiddleware(app)  # Wrap FastAPI so Passenger can load it through the required WSGI entry point