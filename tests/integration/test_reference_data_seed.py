from datetime import (
    UTC,
    datetime,
)  # Import timezone-aware datetime tools for the private mapping test

from sqlalchemy import func, select  # Import aggregate and query tools for database verification
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)  # Import isolated asynchronous database-test tools

from app.commands.seed_reference_data import (
    seed_reference_data,
)  # Import the real production reference-data seed service
from app.data.reference import ALIAS_SEEDS  # Import the canonical alias count for verification
from app.models import metadata  # Import the complete application schema
from app.models.club import (
    Club,
    ClubAlias,
    ClubSourceMapping,
)  # Import club persistence models used by count assertions
from app.models.league import (
    League,
    LeagueMembership,
)  # Import league persistence models used by count assertions
from app.schemas.source_mapping import SourceMappingSeed  # Import validated private mapping input


async def test_reference_data_seed_is_idempotent() -> (
    None
):  # Verify that repeated seed executions never create duplicate reference data
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:"
    )  # Create an isolated asynchronous SQLite database

    try:  # Guarantee temporary engine cleanup after the assertions
        async with engine.begin() as connection:  # Open the isolated schema transaction
            await connection.run_sync(
                metadata.create_all
            )  # Create every application table from the current ORM metadata

        session_factory = async_sessionmaker(
            engine, expire_on_commit=False
        )  # Create isolated asynchronous ORM sessions

        private_mapping = SourceMappingSeed(  # Build one safe fake private mapping for integration testing
            club_slug="sl-benfica",  # Reference a real canonical club
            provider_key="primary_schedule",  # Use the same generic provider identifier as production configuration
            source_slug="example-private-slug",  # Use a non-production fake provider-specific identifier
            source_url="https://example.invalid/private-club",  # Use the reserved invalid example domain rather than a production URL
            verified_at=datetime(
                2026, 8, 21, tzinfo=UTC
            ),  # Record a deterministic timezone-aware test verification date
        )  # Finish the safe private mapping fixture

        async with session_factory() as session:  # Open one isolated asynchronous ORM session
            await seed_reference_data(session, (private_mapping,))  # Execute the real seed once
            await seed_reference_data(
                session, (private_mapping,)
            )  # Execute it again to prove idempotency

            league_count = await session.scalar(
                select(func.count()).select_from(League)
            )  # Count persisted leagues
            club_count = await session.scalar(
                select(func.count()).select_from(Club)
            )  # Count persisted canonical clubs
            membership_count = await session.scalar(
                select(func.count()).select_from(LeagueMembership)
            )  # Count current-season memberships
            alias_count = await session.scalar(
                select(func.count()).select_from(ClubAlias)
            )  # Count deterministic aliases
            mapping_count = await session.scalar(
                select(func.count()).select_from(ClubSourceMapping)
            )  # Count private source mappings

        assert league_count == 2  # Require exactly two professional leagues after repeated seeding
        assert club_count == 36  # Require exactly 36 canonical clubs after repeated seeding
        assert (
            membership_count == 36
        )  # Require exactly 36 current-season memberships after repeated seeding
        assert alias_count == len(
            ALIAS_SEEDS
        )  # Require one row for every canonical alias and no duplicates
        assert mapping_count == 1  # Require the repeated private mapping to remain one database row
    finally:  # Always release the temporary asynchronous database
        await engine.dispose()  # Dispose the isolated engine and all of its connections
