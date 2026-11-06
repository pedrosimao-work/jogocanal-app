from pathlib import Path

from fastapi import FastAPI  # Import FastAPI so the main application object can be created
from fastapi.staticfiles import StaticFiles

from app.api.system import (
    router as system_router,
)  # Import the router containing the application-level operational endpoints
from app.core.config import settings  # Import the validated central application settings
from app.web.routes import router as web_router


def create_app() -> FastAPI:  # Create and configure the FastAPI application
    application = FastAPI(  # Create a new FastAPI application instance
        title=settings.app_name,  # Use the configured application name in OpenAPI and Swagger UI
        version=settings.app_version,  # Use the configured application version
        debug=settings.debug,  # Apply the configured FastAPI debug behaviour
    )  # Finish the FastAPI application configuration

    application.include_router(
        system_router
    )  # Register the permanent system routes with the FastAPI application
    application.mount(
        "/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static"
    )
    application.include_router(web_router)

    return application  # Return the fully configured FastAPI application instance


app = create_app()  # Create the shared FastAPI application instance
