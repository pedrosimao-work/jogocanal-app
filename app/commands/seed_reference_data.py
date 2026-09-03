import argparse  # Import argparse so the seed command can accept an optional private mapping file
import asyncio  # Import asyncio so the command can execute the asynchronous SQLAlchemy workflow
import json  # Import json so private source-mapping files can be decoded
from dataclasses import dataclass  # Import dataclass for the immutable seed-result summary
from pathlib import Path  # Import Path for safe filesystem handling

from pydantic import (
    TypeAdapter,
)  # Import TypeAdapter to validate a complete JSON list with Pydantic
from sqlalchemy import select  # Import select for database-independent ORM lookups
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)  # Import AsyncSession for the asynchronous seed service

from app.data.reference import (  # Import canonical data and typed seed structures
    ALIAS_SEEDS,
    CLUB_SEEDS,
    LEAGUE_SEEDS,
    SEASON_2026_2027,
    AliasSeed,
    ClubSeed,
    LeagueSeed,
)
from app.db.session import (
    async_session_factory,
)  # Import the application's asynchronous session factory
from app.models.club import (
    Club,
    ClubAlias,
    ClubSourceMapping,
)  # Import canonical club persistence models
from app.models.league import (
    League,
    LeagueMembership,
)  # Import league and season-membership persistence models
from app.schemas.source_mapping import SourceMappingSeed  # Import private source-mapping validation

SOURCE_MAPPING_ADAPTER = TypeAdapter(
    list[SourceMappingSeed]
)  # Validate private JSON files as lists of source mappings


@dataclass(frozen=True, slots=True)  # Make the seed summary immutable after one completed execution
class SeedSummary:  # Describe how many canonical records were processed during the seed
    leagues: int  # Count the configured leagues
    clubs: int  # Count the configured clubs
    memberships: int  # Count the current-season league memberships
    aliases: int  # Count deterministic club aliases
    source_mappings: int  # Count private operational source mappings processed


def load_source_mappings(
    path: Path | None,
) -> tuple[SourceMappingSeed, ...]:  # Load optional private operational mappings
    if path is None:  # Allow public reference data to be seeded without private mapping information
        return ()  # Return an empty immutable mapping collection

    raw_data = json.loads(
        path.read_text(encoding="utf-8-sig")
    )  # Decode the ignored private JSON file using UTF-8
    validated = SOURCE_MAPPING_ADAPTER.validate_python(
        raw_data
    )  # Validate every object before touching the database

    keys = [
        (mapping.club_slug, mapping.provider_key) for mapping in validated
    ]  # Build the database uniqueness keys from the private file

    if len(keys) != len(set(keys)):  # Detect duplicate club/provider mappings before persistence
        raise ValueError(
            "Duplicate club/provider source mapping found."
        )  # Stop rather than silently accepting conflicting input

    return tuple(validated)  # Return the validated mappings as an immutable collection


async def _upsert_league(
    session: AsyncSession, seed: LeagueSeed
) -> League:  # Create or update one canonical league
    league = await session.scalar(
        select(League).where(League.slug == seed.slug)
    )  # Find an existing league by stable slug

    if league is None:  # Create the league only when it has not been seeded before
        league = League(  # Build the new canonical league ORM record
            name=seed.name,  # Persist the current canonical league name
            slug=seed.slug,  # Persist the stable league identifier
            tier=seed.tier,  # Persist the domestic league tier
            is_active=True,  # Mark the currently seeded league as active
        )  # Finish the league ORM object
        session.add(league)  # Add the new league to the active transaction
        await session.flush()  # Obtain its database ID before creating memberships
    else:  # Keep an existing league synchronized with canonical seed data
        league.name = seed.name  # Update the canonical league name
        league.tier = seed.tier  # Update the configured domestic tier
        league.is_active = True  # Ensure the current league remains active

    return league  # Return the persisted or updated league


async def _upsert_club(
    session: AsyncSession, seed: ClubSeed
) -> Club:  # Create or update one canonical club
    club = await session.scalar(
        select(Club).where(Club.slug == seed.slug)
    )  # Find the club using its stable application slug

    if club is None:  # Create a new record only when the canonical club does not already exist
        club = Club(  # Build the canonical club ORM record
            name=seed.name,  # Persist the canonical Portuguese club name
            slug=seed.slug,  # Persist the stable application slug
            short_name=seed.short_name,  # Persist the compact public display name
            crest_path=seed.crest_path,  # Persist the relative local crest path
            is_tracked=True,  # Mark every current professional club as tracked by JogoCanal
            is_active=True,  # Mark every current-season club as active
        )  # Finish the new club ORM object
        session.add(club)  # Add the club to the active database transaction
        await session.flush()  # Obtain the generated ID before creating related rows
    else:  # Synchronize an existing club with the canonical seed data
        club.name = seed.name  # Update the canonical club name if necessary
        club.short_name = seed.short_name  # Update the compact display name
        club.crest_path = seed.crest_path  # Update the configured local crest path
        club.is_tracked = True  # Keep the currently seeded club tracked
        club.is_active = True  # Keep the currently seeded club active

    return club  # Return the persisted or updated canonical club


async def _upsert_alias(  # Create or synchronize one deterministic club alias
    session: AsyncSession,  # Receive the active asynchronous database session
    seed: AliasSeed,  # Receive the canonical alias seed definition
    club: Club,  # Receive the already-persisted canonical club
) -> None:  # Update the transaction without returning an ORM record
    alias = await session.scalar(  # Search for the globally unique normalized alias
        select(ClubAlias).where(
            ClubAlias.normalized_alias == seed.normalized_alias
        )  # Match the deterministic lookup key
    )  # Finish the alias lookup

    if alias is None:  # Create the alias when this lookup key does not exist yet
        session.add(  # Add the new alias directly to the current transaction
            ClubAlias(  # Build the deterministic alias record
                club_id=club.id,  # Link the alias to its canonical club
                alias=seed.alias,  # Preserve the representative human-readable alias
                normalized_alias=seed.normalized_alias,  # Persist the deterministic lookup key
            )  # Finish the alias ORM object
        )  # Finish adding the new alias
        return  # Stop because no existing alias requires synchronization

    if (
        alias.club_id != club.id
    ):  # Detect an alias that has been assigned to a different canonical club
        raise ValueError(
            f"Alias conflict: {seed.normalized_alias}"
        )  # Fail rather than silently corrupt canonical resolution

    alias.alias = seed.alias  # Keep the representative raw alias synchronized with seed data


async def _upsert_membership(  # Create or update one club's membership for the current season
    session: AsyncSession,  # Receive the active asynchronous database session
    club: Club,  # Receive the canonical persisted club
    league: League,  # Receive the canonical persisted league
    display_order: int,  # Receive the deterministic public directory position
) -> None:  # Update the current transaction without returning a value
    membership = await session.scalar(  # Look for an existing membership for this club and season
        select(LeagueMembership).where(  # Build the current-season membership query
            LeagueMembership.club_id == club.id,  # Match the canonical club
            LeagueMembership.season == SEASON_2026_2027,  # Match the current professional season
        )  # Finish the membership filters
    )  # Finish the membership lookup

    if membership is None:  # Create the current-season relationship when it does not already exist
        session.add(  # Add the new membership to the transaction
            LeagueMembership(  # Build the new season-membership ORM record
                club_id=club.id,  # Link the membership to the canonical club
                league_id=league.id,  # Link the membership to the correct league
                season=SEASON_2026_2027,  # Record the current football season
                display_order=display_order,  # Persist the stable directory ordering
                is_confirmed=True,  # Mark the now-officially confirmed membership
            )  # Finish the membership ORM object
        )  # Finish adding the new membership
        return  # Stop because no existing membership requires synchronization

    membership.league_id = league.id  # Correct the league if the seed data changed before release
    membership.display_order = display_order  # Synchronize the deterministic public ordering
    membership.is_confirmed = True  # Mark this current-season membership as confirmed


async def _upsert_source_mapping(  # Create or synchronize one private operational source mapping
    session: AsyncSession,  # Receive the active asynchronous database session
    seed: SourceMappingSeed,  # Receive the validated private mapping
    club: Club,  # Receive the canonical persisted club
) -> None:  # Update the current transaction without returning a value
    mapping = await session.scalar(  # Find the existing mapping for this club and provider
        select(ClubSourceMapping).where(  # Build the unique club/provider lookup
            ClubSourceMapping.club_id == club.id,  # Match the canonical club
            ClubSourceMapping.provider_key
            == seed.provider_key,  # Match the generic provider identifier
        )  # Finish the source-mapping filters
    )  # Finish the source-mapping lookup

    if mapping is None:  # Create the mapping when this club/provider relationship is new
        session.add(  # Add the private mapping to the active transaction
            ClubSourceMapping(  # Build the operational source-mapping record
                club_id=club.id,  # Link the mapping to the canonical club
                provider_key=seed.provider_key,  # Persist only the generic internal provider identifier
                source_slug=seed.source_slug,  # Persist the private provider-specific club identifier
                source_url=str(seed.source_url),  # Persist the validated private operational URL
                verified_at=seed.verified_at,  # Record when the mapping was manually verified
                is_active=True,  # Mark the current verified mapping as active
            )  # Finish the source-mapping ORM object
        )  # Finish adding the new source mapping
        return  # Stop because no existing mapping requires synchronization

    mapping.source_slug = seed.source_slug  # Synchronize the private provider-specific identifier
    mapping.source_url = str(seed.source_url)  # Synchronize the private operational URL
    mapping.verified_at = seed.verified_at  # Preserve the actual manual verification date
    mapping.is_active = True  # Reactivate the mapping if the current audit confirms it


async def seed_reference_data(  # Seed all canonical reference data in one atomic transaction
    session: AsyncSession,  # Receive the asynchronous database session used for persistence
    source_mappings: tuple[
        SourceMappingSeed, ...
    ] = (),  # Optionally receive validated private source mappings
) -> SeedSummary:  # Return a deterministic summary of the processed reference data
    leagues_by_slug: dict[
        str, League
    ] = {}  # Keep persisted leagues available for membership creation
    clubs_by_slug: dict[
        str, Club
    ] = {}  # Keep persisted clubs available for aliases, memberships, and mappings

    async with (
        session.begin()
    ):  # Commit all reference changes together or roll everything back on failure
        for league_seed in LEAGUE_SEEDS:  # Process every configured professional league
            league = await _upsert_league(session, league_seed)  # Create or synchronize the league
            leagues_by_slug[league_seed.slug] = league  # Store the persisted league by stable slug

        for club_seed in CLUB_SEEDS:  # Process all 36 current professional clubs
            club = await _upsert_club(
                session, club_seed
            )  # Create or synchronize the canonical club
            clubs_by_slug[club_seed.slug] = club  # Store the persisted club by stable slug

        for alias_seed in ALIAS_SEEDS:  # Process every deterministic alias definition
            club = clubs_by_slug[
                alias_seed.club_slug
            ]  # Resolve the alias's canonical persisted club
            await _upsert_alias(session, alias_seed, club)  # Create or synchronize the alias

        membership_count = 0  # Count the season memberships processed during this execution

        for league_seed in LEAGUE_SEEDS:  # Process memberships league by league
            league = leagues_by_slug[league_seed.slug]  # Resolve the persisted canonical league

            for display_order, club_slug in enumerate(
                league_seed.club_slugs, start=1
            ):  # Assign stable one-based public ordering
                club = clubs_by_slug[club_slug]  # Resolve the canonical persisted club
                await _upsert_membership(
                    session, club, league, display_order
                )  # Create or synchronize the membership
                membership_count += 1  # Record that one current-season membership was processed

        for (
            mapping_seed
        ) in source_mappings:  # Process only private mappings supplied by the local operator
            source_club = clubs_by_slug.get(
                mapping_seed.club_slug
            )  # Resolve the private mapping's canonical club safely

            if (
                source_club is None
            ):  # Reject mappings referring to clubs outside the canonical reference set
                raise ValueError(  # Stop the transaction instead of accepting invalid private reference data
                    f"Unknown club slug in source mapping: {mapping_seed.club_slug}"
                    # Identify the invalid canonical club slug
                )  # Finish the validation error

            await _upsert_source_mapping(  # Create or synchronize the private operational mapping
                session,  # Use the active asynchronous database session
                mapping_seed,  # Pass the validated private mapping definition
                source_club,  # Pass the guaranteed canonical Club rather than an optional lookup result
            )  # Finish the private source-mapping upsert

    return SeedSummary(  # Return deterministic counts after the successful transaction commits
        leagues=len(LEAGUE_SEEDS),  # Report the number of professional leagues processed
        clubs=len(CLUB_SEEDS),  # Report the number of canonical clubs processed
        memberships=membership_count,  # Report the number of current-season memberships processed
        aliases=len(ALIAS_SEEDS),  # Report the number of deterministic aliases processed
        source_mappings=len(source_mappings),  # Report the number of private mappings processed
    )  # Finish the seed summary


def _parse_args() -> (
    argparse.Namespace
):  # Parse optional command-line input for private source mappings
    parser = argparse.ArgumentParser(
        description="Seed canonical JogoCanal reference data."
    )  # Create the seed-command parser
    parser.add_argument(  # Add the optional ignored private mapping-file argument
        "--source-mappings",  # Define the command-line option name
        type=Path,  # Convert the supplied path into a pathlib Path object
        default=None,  # Allow canonical public data to be seeded without private mappings
        help="Path to the ignored private source-mapping JSON file.",  # Explain the operational purpose without naming a provider
    )  # Finish the optional source-mapping argument
    return parser.parse_args()  # Parse and return the current command-line arguments


async def _run() -> None:  # Execute the asynchronous seed command
    args = _parse_args()  # Read the optional private mapping-file argument
    source_mappings = load_source_mappings(
        args.source_mappings
    )  # Validate the private file before opening a database transaction

    async with (
        async_session_factory() as session
    ):  # Open an application-configured asynchronous database session
        summary = await seed_reference_data(
            session, source_mappings
        )  # Seed canonical and optional private reference data

    print(  # Display a concise operational summary after the successful seed
        f"Seeded leagues={summary.leagues}, clubs={summary.clubs}, "  # Report the canonical league and club counts
        f"memberships={summary.memberships}, aliases={summary.aliases}, "  # Report current-season memberships and aliases
        f"source_mappings={summary.source_mappings}"  # Report how many private mappings were processed
    )  # Finish the command summary


def main() -> None:  # Provide the synchronous module entry point used by the terminal
    asyncio.run(_run())  # Execute the asynchronous seeding workflow


if __name__ == "__main__":  # Run the command only when this module is executed directly
    main()  # Start the reference-data seed process
