from httpx import (
    AsyncClient,
)  # Import the asynchronous HTTP client type used by the shared test fixture


async def test_health_checks(
    client: AsyncClient,
) -> None:  # Verify that the FastAPI health endpoint behaves correctly through ASGI
    response = await client.get(
        "/health"
    )  # Send an asynchronous GET request to the health endpoint

    assert response.status_code == 200  # Confirm that a healthy application returns HTTP 200 OK
    assert response.json() == {
        "status": "ok",
        "framework": "FastAPI",
    }  # Confirm that FastAPI returns the expected validated JSON response
