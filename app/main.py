from fastapi import FastAPI  # Import FastAPI so the JogoCanal web application can be created


app = FastAPI(  # Create the central FastAPI application object
    title="JogoCanal",  # Set the application name shown in the generated API documentation
    version="0.1.0",  # Record the initial application version for this compatibility milestone
)  # Finish the FastAPI application configuration


@app.get("/health", tags=["system"])  # Register a read-only endpoint used to verify that the application is running
def health_check() -> dict[str, str]:  # Define a synchronous health check that returns string keys and values
    return {  # Return a small JSON response that confirms the framework is operational
        "status": "ok",  # Confirm that the application successfully processed the request
        "framework": "FastAPI",  # Confirm that the response came from the FastAPI application
    }  # Finish the health-check response