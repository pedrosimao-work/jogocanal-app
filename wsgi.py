from threading import Lock  # Import Lock so simultaneous first requests cannot create multiple adapters
from typing import Any, Callable, Iterable  # Import type-hint tools for the WSGI callable interface

from a2wsgi import ASGIMiddleware  # Import the adapter that exposes FastAPI through WSGI

from app.main import app  # Import the real FastAPI application


_adapter: ASGIMiddleware | None = None  # Store the adapter after it is created inside the Passenger worker
_adapter_lock = Lock()  # Protect the one-time adapter creation from concurrent requests


def application(  # Define the WSGI callable that Passenger loads
    environ: dict[str, Any],  # Receive the request environment supplied by Passenger
    start_response: Callable[..., Any],  # Receive the WSGI callback used to begin the HTTP response
) -> Iterable[bytes]:  # Return the response body as an iterable of byte chunks
    global _adapter  # Allow this function to save the adapter in the module-level variable

    if _adapter is None:  # Check whether this Passenger worker still needs its adapter
        with _adapter_lock:  # Allow only one request to perform the initial creation
            if _adapter is None:  # Check again after acquiring the lock
                _adapter = ASGIMiddleware(app)  # Start the ASGI event loop inside the active worker process

    return _adapter(environ, start_response)  # Forward the WSGI request to the FastAPI application