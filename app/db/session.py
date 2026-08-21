from typing import Any  # Import Any for the low-level database connection callback types

from sqlalchemy import (
    event,
)  # Import SQLAlchemy events so SQLite foreign keys can be enabled per connection
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)  # Import asynchronous SQLAlchemy engine and session tools

from app.core.config import settings  # Import the validated database configuration

engine = create_async_engine(  # Create the application's asynchronous SQLAlchemy database engine
    settings.database_url,  # Connect using the environment-aware database URL
    echo=settings.debug,  # Log generated SQL statements only while application debug mode is enabled
)  # Finish the asynchronous engine configuration


async_session_factory = async_sessionmaker(  # Create the reusable asynchronous ORM session factory
    bind=engine,  # Bind every generated session to the shared asynchronous engine
    class_=AsyncSession,  # Require generated sessions to use SQLAlchemy's asynchronous session class
    expire_on_commit=False,  # Keep loaded ORM attributes available after a successful commit
)  # Finish the asynchronous session factory configuration


def _enable_sqlite_foreign_keys(  # Define the connection callback used only by the local SQLite database
    dbapi_connection: Any,  # Receive SQLAlchemy's adapted low-level database connection
    connection_record: Any,  # Receive SQLAlchemy's connection-pool record for this connection
) -> None:  # Configure the connection without returning a value
    del (
        connection_record
    )  # Explicitly discard the unused pool record while keeping the required callback signature
    cursor = (
        dbapi_connection.cursor()
    )  # Open a low-level cursor on the newly created SQLite connection
    cursor.execute(
        "PRAGMA foreign_keys=ON"
    )  # Enable SQLite foreign-key constraint enforcement for this connection
    cursor.close()  # Close the temporary cursor after configuring the connection


if settings.database_url.startswith(
    "sqlite"
):  # Apply the SQLite-specific connection rule only to SQLite databases
    event.listen(
        engine.sync_engine, "connect", _enable_sqlite_foreign_keys
    )  # Register foreign-key enforcement for every SQLite connection
