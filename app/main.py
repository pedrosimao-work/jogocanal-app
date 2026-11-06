from pathlib import Path

from fastapi import FastAPI  # Import FastAPI so the main application object can be created
from fastapi.staticfiles import StaticFiles

from app.admin.auth import router as admin_router
from app.admin.dashboard import router as dashboard_router
from app.api.system import (
    router as system_router,
)  # Import the router containing the application-level operational endpoints
from app.api.v1.routes import router as public_router
from app.core.config import settings  # Import the validated central application settings
from app.core.security_headers import SecurityHeaders
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
    application.include_router(public_router)
    application.include_router(admin_router)
    application.include_router(dashboard_router)
    application.add_middleware(SecurityHeaders)

    return application  # Return the fully configured FastAPI application instance


app = create_app()  # Create the shared FastAPI application instance
