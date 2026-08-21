from sqlalchemy import inspect  # Import SQLAlchemy's database-schema inspection function
from sqlalchemy.engine import (
    Connection,
)  # Import the synchronous connection type used inside AsyncConnection.run_sync
from sqlalchemy.ext.asyncio import (
    create_async_engine,
)  # Import the asynchronous engine creator for isolated schema testing
from sqlalchemy.orm import (
    configure_mappers,
)  # Import mapper validation so relationship configuration can be tested

from app.models import metadata  # Import the complete JogoCanal model metadata

EXPECTED_TABLES = {  # Define every application table that must exist in the initial schema
    "admin_users",  # Store private administrator accounts
    "channels",  # Store canonical broadcast channels
    "club_aliases",  # Store deterministic alternative club names
    "club_source_mappings",  # Store operational source mappings
    "clubs",  # Store canonical football clubs
    "competitions",  # Store canonical competitions
    "league_memberships",  # Store club-to-league relationships for individual seasons
    "leagues",  # Store football leagues
    "match_channels",  # Store the many-to-many match/channel relationship
    "matches",  # Store canonical televised matches
    "normalisation_cache",  # Store reusable normalisation results
    "scrape_jobs",  # Store durable manual scrape requests
    "scrape_run_events",  # Store structured scraper execution events
    "scrape_runs",  # Store scraper execution summaries
}  # Finish the expected initial schema table set


def _get_table_names(
    connection: Connection,
) -> set[str]:  # Read table names through SQLAlchemy's synchronous inspection API
    inspector = inspect(connection)  # Create a schema inspector for the active test connection
    return set(inspector.get_table_names())  # Return all created table names as an unordered set


async def test_metadata_creates_expected_tables() -> (
    None
):  # Verify that the complete ORM metadata produces the expected database schema
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:"
    )  # Create an isolated asynchronous in-memory SQLite database

    try:  # Guarantee engine cleanup even if schema creation or assertions fail
        async with (
            engine.begin() as connection
        ):  # Open an asynchronous transactional database connection
            await connection.run_sync(
                metadata.create_all
            )  # Create the complete JogoCanal schema using the ORM metadata
            table_names = await connection.run_sync(
                _get_table_names
            )  # Inspect the created tables through the synchronous inspection bridge

        assert (
            table_names == EXPECTED_TABLES
        )  # Confirm that every planned application table exists and no unexpected table was introduced
    finally:  # Always release the temporary asynchronous engine
        await engine.dispose()  # Close the isolated database engine and its connections


def test_model_relationships_configure() -> (
    None
):  # Verify that all ORM relationship references can be resolved successfully
    configure_mappers()  # Force SQLAlchemy to configure every mapped relationship and raise if any relationship is invalid
