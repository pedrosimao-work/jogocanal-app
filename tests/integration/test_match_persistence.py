from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import metadata
from app.models.channel import Channel
from app.models.club import Club
from app.models.competition import Competition
from app.models.match import Match, MatchChannel
from app.models.scrape import ScrapeRun, ScrapeRunEvent
from app.schemas.ingestion import MatchInput, SourceBatch
from app.services.ingestion import match_fingerprint, persist_run

NOW = datetime(2026, 11, 6, 8, tzinfo=UTC)


@pytest_asyncio.fixture
async def sessions() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory.begin() as session:
        session.add_all(
            [
                Competition(id=1, name="Example Cup", slug="example-cup"),
                Channel(id=1, name="Channel One", slug="channel-one"),
                Channel(id=2, name="Channel Two", slug="channel-two"),
                Club(id=1, name="Home FC", short_name="Home", slug="home"),
                Club(id=2, name="Away FC", short_name="Away", slug="away"),
            ]
        )
    try:
        yield factory
    finally:
        await engine.dispose()


def match(**changes: object) -> MatchInput:
    values = dict(
        kickoff_at=NOW + timedelta(hours=12),
        home_name_raw="Home",
        away_name_raw="Away",
        home_name_display="Home FC",
        away_name_display="Away FC",
        home_club_id=1,
        away_club_id=2,
        competition_id=1,
        channel_ids={1},
    )
    values.update(changes)
    return MatchInput.model_validate(values)


def batch(matches: tuple[MatchInput, ...] = (), **changes: object) -> SourceBatch:
    values = dict(
        reference="daily",
        matches=matches,
        complete=True,
        window_start=NOW,
        window_end=NOW + timedelta(days=2),
    )
    values.update(changes)
    return SourceBatch.model_validate(values)


async def test_duplicate_pages_merge_channels_and_repeated_runs_replace(sessions) -> None:
    first = match()
    second = match(channel_ids={2})
    run_id = await persist_run(
        sessions, (batch((first,)), batch((second,), reference="club")), observed_at=NOW
    )
    async with sessions() as session:
        rows = list(await session.scalars(select(Match)))
        assert len(rows) == 1
        assert set(await session.scalars(select(MatchChannel.channel_id))) == {1, 2}
        run = await session.get(ScrapeRun, run_id)
        assert run.status == "completed" and run.matches_created == 1
    await persist_run(sessions, (batch((second,)),), observed_at=NOW + timedelta(hours=1))
    async with sessions() as session:
        assert len(list(await session.scalars(select(Match)))) == 1
        assert set(await session.scalars(select(MatchChannel.channel_id))) == {2}


@pytest.mark.parametrize(
    "changes", [{"successful": False}, {}, {"complete": False, "allow_empty": True}]
)
async def test_failed_partial_and_unconfirmed_empty_preserve_matches(sessions, changes) -> None:
    await persist_run(sessions, (batch((match(),)),), observed_at=NOW)
    await persist_run(sessions, (batch(**changes),), observed_at=NOW + timedelta(hours=1))
    async with sessions() as session:
        record = (await session.scalars(select(Match))).one()
        assert not record.is_stale


async def test_confirmed_empty_marks_stale_and_reappearance_recovers(sessions) -> None:
    await persist_run(sessions, (batch((match(),)),), observed_at=NOW)
    await persist_run(sessions, (batch(allow_empty=True),), observed_at=NOW + timedelta(hours=1))
    async with sessions() as session:
        assert (await session.scalars(select(Match))).one().is_stale
    await persist_run(sessions, (batch((match(),)),), observed_at=NOW + timedelta(hours=2))
    async with sessions() as session:
        assert not (await session.scalars(select(Match))).one().is_stale


async def test_invalid_batch_rolls_back_all_its_matches_and_logs_failure(sessions) -> None:
    invalid = match(channel_ids={999}, kickoff_at=NOW + timedelta(hours=13))
    run_id = await persist_run(sessions, (batch((match(), invalid)),), observed_at=NOW)
    async with sessions() as session:
        assert list(await session.scalars(select(Match))) == []
        run = await session.get(ScrapeRun, run_id)
        assert run.status == "failed" and run.error_count == 1 and run.matches_created == 0
        event = (await session.scalars(select(ScrapeRunEvent))).one()
        assert event.error_type == "SourceBatchFailure" and "999" not in event.message


async def test_partial_run_keeps_successful_sources(sessions) -> None:
    run_id = await persist_run(
        sessions,
        (
            batch((match(),)),
            batch(reference="club", successful=False),
        ),
        observed_at=NOW,
    )
    async with sessions() as session:
        assert len(list(await session.scalars(select(Match)))) == 1
        run = await session.get(ScrapeRun, run_id)
        assert (
            run.status == "partial" and run.sources_successful == 1 and run.sources_attempted == 2
        )


async def test_older_snapshot_does_not_overwrite_newer_channels(sessions) -> None:
    await persist_run(
        sessions, (batch((match(channel_ids={2}),)),), observed_at=NOW + timedelta(hours=1)
    )
    await persist_run(sessions, (batch((match(),)),), observed_at=NOW)
    async with sessions() as session:
        assert set(await session.scalars(select(MatchChannel.channel_id))) == {2}


async def test_older_source_revision_is_ignored(sessions) -> None:
    await persist_run(
        sessions, (batch((match(channel_ids={2}, source_updated_at=NOW),)),), observed_at=NOW
    )
    await persist_run(
        sessions,
        (batch((match(source_updated_at=NOW - timedelta(hours=1)),)),),
        observed_at=NOW + timedelta(hours=1),
    )
    async with sessions() as session:
        assert set(await session.scalars(select(MatchChannel.channel_id))) == {2}


async def test_scope_preserves_past_other_clubs_and_other_provider(sessions) -> None:
    other = match(home_club_id=None, away_club_id=None, home_name_display="Other FC")
    past = match(kickoff_at=NOW - timedelta(hours=1))
    await persist_run(
        sessions,
        (
            batch((match(), other, past), complete=False),
            batch((match(),), reference="other", provider_key="other"),
        ),
        observed_at=NOW,
    )
    await persist_run(
        sessions, (batch(allow_empty=True, club_id=1),), observed_at=NOW + timedelta(hours=1)
    )
    async with sessions() as session:
        rows = list(await session.scalars(select(Match)))
        assert sum(row.is_stale for row in rows) == 1


def test_fingerprint_equivalent_utc_and_channel_independence() -> None:
    first = match()
    assert match_fingerprint(first) == match_fingerprint(
        match(kickoff_at=first.kickoff_at.astimezone(timezone(timedelta(hours=2))))
    )
    assert match_fingerprint(first) == match_fingerprint(match(channel_ids={2}))
    assert match_fingerprint(first) != match_fingerprint(
        match(away_club_id=None, away_name_display="Away B")
    )
    assert match_fingerprint(first) != match_fingerprint(first, "other")


def test_invalid_coverage_rejected() -> None:
    with pytest.raises(ValueError):
        batch((match(),), club_id=3)
    with pytest.raises(ValueError):
        batch(window_end=NOW)
    with pytest.raises(ValueError):
        batch((match(),), successful=False)
    with pytest.raises(ValueError):
        match(kickoff_at=datetime(2026, 11, 6))


async def test_empty_coverage_warning_and_review_counters(sessions) -> None:
    run_id = await persist_run(
        sessions,
        (
            batch((match(needs_review=True, unknown_terms=2),)),
            batch(reference="empty"),
        ),
        observed_at=NOW,
    )
    async with sessions() as session:
        run = await session.get(ScrapeRun, run_id)
        assert run.unknown_terms == 2 and run.finished_at is not None
        assert (await session.scalars(select(Match))).one().needs_review
        warnings = list(
            await session.scalars(select(ScrapeRunEvent).where(ScrapeRunEvent.level == "warning"))
        )
        assert len(warnings) == 1 and warnings[0].source_reference == "empty"


@pytest.mark.parametrize("changes", [{"competition_id": 999}, {"home_club_id": 999}])
async def test_missing_catalogue_references_fail_safely(sessions, changes) -> None:
    run_id = await persist_run(sessions, (batch((match(**changes),)),), observed_at=NOW)
    async with sessions() as session:
        assert (await session.get(ScrapeRun, run_id)).status == "failed"
        assert not list(await session.scalars(select(Match)))
