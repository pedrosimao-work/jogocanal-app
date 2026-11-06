from collections.abc import (
    AsyncIterator,
)  # Import AsyncIterator so the asynchronous test fixture has an explicit return type

import pytest_asyncio  # Import pytest-asyncio so pytest can create an asynchronous fixture
from httpx import (
    ASGITransport,
    AsyncClient,
)  # Import HTTPX tools for sending requests directly to the FastAPI ASGI application
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.dependencies import get_db_session
from app.main import app  # Import the real FastAPI application that the tests must exercise
from app.models import metadata


@pytest_asyncio.fixture
async def web_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        await engine.dispose()


@pytest_asyncio.fixture  # Register this asynchronous function as a reusable pytest fixture
async def client(
    web_session: AsyncSession,
) -> AsyncIterator[AsyncClient]:  # Provide an asynchronous HTTP client to route tests
    transport = ASGITransport(
        app=app
    )  # Connect HTTPX directly to FastAPI through its native ASGI interface

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield web_session

    app.dependency_overrides[get_db_session] = override_session
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
            yield async_client
    finally:
        app.dependency_overrides.pop(get_db_session, None)
