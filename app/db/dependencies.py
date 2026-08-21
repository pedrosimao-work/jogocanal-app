from collections.abc import (
    AsyncIterator,
)  # Import AsyncIterator for the asynchronous dependency return type

from sqlalchemy.ext.asyncio import AsyncSession  # Import the asynchronous ORM session type

from app.db.session import async_session_factory  # Import the shared asynchronous session factory


async def get_db_session() -> AsyncIterator[
    AsyncSession
]:  # Provide one asynchronous database session per FastAPI dependency request
    async with (
        async_session_factory() as session
    ):  # Open a session and guarantee that it closes after the request
        yield session  # Provide the active asynchronous session to the requesting route or dependency
