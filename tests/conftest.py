from collections.abc import (
    AsyncIterator,
)  # Import AsyncIterator so the asynchronous test fixture has an explicit return type

import pytest_asyncio  # Import pytest-asyncio so pytest can create an asynchronous fixture
from httpx import (
    ASGITransport,
    AsyncClient,
)  # Import HTTPX tools for sending requests directly to the FastAPI ASGI application

from app.main import app  # Import the real FastAPI application that the tests must exercise


@pytest_asyncio.fixture  # Register this asynchronous function as a reusable pytest fixture
async def client() -> AsyncIterator[
    AsyncClient
]:  # Provide an asynchronous HTTP client to route tests
    transport = ASGITransport(
        app=app
    )  # Connect HTTPX directly to FastAPI through its native ASGI interface

    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as async_client:  # Create and safely manage the asynchronous test client
        yield async_client  # Provide the configured client to each test that requests the fixture
