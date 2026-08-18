from fastapi import (
    APIRouter,
)  # Import APIRouter so related application endpoints can be grouped outside main.py

from app.schemas.system import (
    HealthResponse,
)  # Import the validated response schema used by the health endpoint

router = APIRouter(
    tags=["system"]
)  # Create the router containing operational application endpoints


@router.get(
    "/health", response_model=HealthResponse, summary="Health check"
)  # Register the permanent application health endpoint
async def health_check() -> (
    HealthResponse
):  # Handle the health request asynchronously using the application's ASGI-first design
    return HealthResponse()  # Return the validated health response defined by the Pydantic schema
