from typing import Literal  # Import Literal so the health response contains exact documented values

from pydantic import BaseModel  # Import BaseModel so FastAPI can validate and document the response


class HealthResponse(
    BaseModel
):  # Define the validated response returned by the application health endpoint
    status: Literal["ok"] = (
        "ok"  # Guarantee that a healthy application returns the exact status value "ok"
    )
    framework: Literal["FastAPI"] = (
        "FastAPI"  # Identify FastAPI as the framework serving the application
    )
