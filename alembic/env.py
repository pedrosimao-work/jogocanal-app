import asyncio  # Import asyncio so synchronous Alembic commands can execute through the asynchronous SQLAlchemy engine
from logging.config import (
    fileConfig,  # Import logging configuration support for the generated Alembic configuration
)

from sqlalchemy.engine import (
    Connection,  # Import the synchronous connection type used by Alembic's migration context
)
from sqlalchemy.ext.asyncio import (
    create_async_engine,  # Import the asynchronous SQLAlchemy engine creator
)
from sqlalchemy.pool import (
    NullPool,  # Import NullPool so migration processes do not keep persistent database connections
)

from alembic import context  # Import the active Alembic migration environment
from app.core.config import (
    settings,  # Import the application's environment-aware database configuration
)
from app.models import (
    metadata,  # Import every registered model through the complete SQLAlchemy metadata collection
)

config = context.config  # Access the Alembic configuration associated with the current command


if (
    config.config_file_name is not None
):  # Configure Alembic logging when an INI configuration file is available
    fileConfig(config.config_file_name)  # Load the logging configuration from alembic.ini


target_metadata = metadata  # Give Alembic the complete ORM schema used for migration autogeneration


def run_migrations_offline() -> (
    None
):  # Configure migration generation without opening a real database connection
    context.configure(  # Configure Alembic's offline migration environment
        url=settings.database_url,  # Use the same environment-aware database URL as the application
        target_metadata=target_metadata,  # Compare migrations against the complete SQLAlchemy model metadata
        literal_binds=True,  # Render literal SQL values directly when producing offline migration SQL
        dialect_opts={
            "paramstyle": "named"
        },  # Use named parameters when Alembic renders SQL without a live connection
        compare_type=True,  # Detect meaningful SQL column-type changes during autogeneration
    )  # Finish the offline migration configuration

    with context.begin_transaction():  # Open Alembic's offline migration transaction context
        context.run_migrations()  # Execute the requested migration operations


def do_run_migrations(
    connection: Connection,
) -> None:  # Execute Alembic's synchronous migration API on an active database connection
    context.configure(  # Configure Alembic using the active connection
        connection=connection,  # Bind migration operations to the current SQLAlchemy connection
        target_metadata=target_metadata,  # Compare the database against the complete ORM metadata
        compare_type=True,  # Detect meaningful column-type differences during autogeneration
    )  # Finish the connected migration configuration

    with context.begin_transaction():  # Open the migration transaction
        context.run_migrations()  # Execute the requested schema migration operations


async def run_async_migrations() -> (
    None
):  # Create an asynchronous engine and adapt Alembic's synchronous migration operations to it
    connectable = create_async_engine(  # Create a temporary asynchronous migration engine
        settings.database_url,  # Use the same environment-aware database URL as the application
        poolclass=NullPool,  # Avoid retaining migration connections after the Alembic process exits
    )  # Finish the migration-engine configuration

    async with (
        connectable.connect() as connection
    ):  # Open an asynchronous database connection for the migration
        await connection.run_sync(
            do_run_migrations
        )  # Adapt Alembic's synchronous migration API to the async connection

    await connectable.dispose()  # Explicitly release the temporary migration engine


def run_migrations_online() -> (
    None
):  # Bridge the normal Alembic CLI into the asynchronous migration implementation
    asyncio.run(
        run_async_migrations()
    )  # Execute the asynchronous migration coroutine from the synchronous CLI entry point


if (
    context.is_offline_mode()
):  # Determine whether Alembic was invoked in offline SQL-generation mode
    run_migrations_offline()  # Run migrations without opening a live database connection
else:  # Handle the normal connected migration mode
    run_migrations_online()  # Run migrations through the asynchronous SQLAlchemy engine
