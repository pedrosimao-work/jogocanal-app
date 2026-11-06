import argparse
import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.commands.seed_catalogue import Catalogue, seed_catalogue
from app.commands.seed_reference_data import seed_reference_data
from app.models import metadata
from app.models.channel import Channel
from app.models.club import Club, ClubSourceMapping
from app.models.match import Match
from app.models.scrape import ScrapeRun
from app.scraper.schemas import ScrapedMatch
from app.services.scrape_pipeline import scrape_pipeline


async def test_cancellation_marks_started_run_failed(factory) -> None:
    ready = asyncio.Event()

    class WaitingReader(Reader):
        async def daily_schedule(self, *, reference_date: date) -> tuple[ScrapedMatch, ...]:
            ready.set()
            await asyncio.Event().wait()
            return ()

    task = asyncio.create_task(
        scrape_pipeline(factory, WaitingReader(), reference_date=date(2026, 11, 6))
    )
    await asyncio.wait_for(ready.wait(), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    async with factory() as session:
        run = (await session.scalars(select(ScrapeRun))).one()
        assert run.status == "failed" and run.finished_at is not None


async def test_real_command_execute_uses_pipeline_and_cleans_resources(
    factory, monkeypatch, tmp_path
) -> None:
    from app.commands.scrape import execute
    from app.core.config import settings
    from app.db import session as database
    from app.scraper import client, config

    class ContextReader(Reader):
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    async with factory.begin() as session:
        await seed_catalogue(session, CATALOGUE)
    monkeypatch.setattr(database, "async_session_factory", factory)
    disposable = AsyncMock()
    monkeypatch.setattr(database, "engine", disposable)
    monkeypatch.setattr(client, "ScheduleSourceClient", lambda config: ContextReader())
    monkeypatch.setattr(config, "load_schedule_source_config", lambda path: None)
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "groq_model", None)
    code = await execute(
        argparse.Namespace(config=tmp_path / "config.json", timeout=30, delay=0, trigger="manual")
    )
    assert code == 0
    disposable.dispose.assert_awaited_once()
    async with factory() as session:
        assert (await session.scalars(select(ScrapeRun))).one().trigger == "manual"


async def test_invalid_catalogue_rolls_back(factory) -> None:
    invalid = Catalogue.model_validate(
        {
            "competitions": [{"name": "Example Cup", "slug": "example-cup"}],
            "channels": [{"name": "One", "slug": "same"}, {"name": "Two", "slug": "same"}],
        }
    )
    with pytest.raises(ValueError):
        async with factory.begin() as session:
            await seed_catalogue(session, invalid)
    async with factory() as session:
        assert not list(await session.scalars(select(Channel)))


@pytest_asyncio.fixture
async def factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            await seed_reference_data(session)
        yield sessions
    finally:
        await engine.dispose()


CATALOGUE = Catalogue.model_validate(
    {
        "competitions": [{"name": "Example Cup", "slug": "example-cup"}],
        "channels": [{"name": "Example Channel", "slug": "example-channel"}],
    }
)


class Reader:
    def __init__(self, fail_club: bool = False) -> None:
        self.fail_club = fail_club
        self.calls = 0

    async def daily_schedule(self, *, reference_date: date) -> tuple[ScrapedMatch, ...]:
        self.calls += 1
        return (
            ScrapedMatch(
                kickoff_at=datetime(2026, 11, 8, 20, tzinfo=UTC),
                home_name_raw="Benfica",
                away_name_raw="Porto",
                competition_raw="Example Cup",
                channels_raw=("Example Channel",),
                source_kind="daily_schedule",
            ),
        )

    async def club_schedule(self, url: str, *, reference_date: date) -> tuple[ScrapedMatch, ...]:
        if self.fail_club:
            raise ValueError("private source details")
        return await self.daily_schedule(reference_date=reference_date)


async def test_pipeline_connects_catalogue_fetch_normalisation_persistence(factory) -> None:
    async with factory.begin() as session:
        await seed_catalogue(session, CATALOGUE)
        await seed_catalogue(session, CATALOGUE)
        club = (await session.scalars(select(Club).where(Club.slug == "sl-benfica"))).one()
        session.add(
            ClubSourceMapping(
                club_id=club.id,
                provider_key="primary_schedule",
                source_slug="example",
                source_url="https://example.invalid/club",
            )
        )
    reader = Reader()
    run_id, status = await scrape_pipeline(
        factory, reader, reference_date=date(2026, 11, 6), delay=0
    )
    assert status == "completed" and reader.calls == 2
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(Channel)) == 1
        record = (await session.scalars(select(Match))).one()
        assert record.home_name_display == "SL Benfica" and record.away_name_display == "FC Porto"
        assert record.home_club_id is not None and not record.needs_review
        assert (await session.get(ScrapeRun, run_id)).sources_successful == 2
    _, status = await scrape_pipeline(
        factory, Reader(True), reference_date=date(2026, 11, 6), delay=0
    )
    assert status == "partial"


async def test_missing_catalogue_fails_without_creating_guessed_entities(factory) -> None:
    _, status = await scrape_pipeline(factory, Reader(), reference_date=date(2026, 11, 6), delay=0)
    assert status == "failed"
    async with factory() as session:
        assert not list(await session.scalars(select(Match)))
        assert not list(await session.scalars(select(Channel)))


async def test_pipeline_carries_source_status(factory):
    class StatusReader(Reader):
        async def daily_schedule(self, *, reference_date):
            items = await super().daily_schedule(reference_date=reference_date)
            return tuple(item.model_copy(update={"source_status": "ADIADO"}) for item in items)

    async with factory.begin() as session:
        await seed_catalogue(session, CATALOGUE)
    await scrape_pipeline(factory, StatusReader(), reference_date=date(2026, 11, 6))
    async with factory() as session:
        record = (await session.scalars(select(Match))).one()
        assert record.source_status == "ADIADO"
