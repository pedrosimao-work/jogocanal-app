"""Connect schedule retrieval, reviewed catalogue resolution and persistence."""

import asyncio
from datetime import date, datetime
from typing import Literal, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.channel import Channel
from app.models.club import Club, ClubSourceMapping
from app.models.competition import Competition
from app.models.mixins import utc_now
from app.models.scrape import ScrapeJob, ScrapeRun, ScrapeRunEvent
from app.schemas.ingestion import MatchInput, SourceBatch
from app.scraper.schemas import ScrapedMatch
from app.services.ingestion import persist_run
from app.services.normalisation import NameFallback, NameNormaliser


class ScheduleReader(Protocol):
    async def daily_schedule(self, *, reference_date: date) -> tuple[ScrapedMatch, ...]: ...

    async def club_schedule(
        self, url: str, *, reference_date: date
    ) -> tuple[ScrapedMatch, ...]: ...


async def prepare_match(
    session: AsyncSession,
    item: ScrapedMatch,
    fallback: NameFallback | None,
) -> MatchInput:
    normaliser = NameNormaliser(session, fallback)
    home = await normaliser.normalise(item.home_name_raw, "club")
    away = await normaliser.normalise(item.away_name_raw, "club")
    competition = await normaliser.normalise(item.competition_raw, "competition")
    channels = [await normaliser.normalise(name, "channel") for name in item.channels_raw]
    competition_record = (
        await session.scalars(
            select(Competition).where(
                Competition.name == competition.value,
                Competition.is_active.is_(True),
            )
        )
    ).one_or_none()
    channel_ids = set(
        await session.scalars(
            select(Channel.id).where(
                Channel.name.in_({channel.value for channel in channels}),
                Channel.is_active.is_(True),
            )
        )
    )
    if competition_record is None or len(channel_ids) != len(
        {channel.value for channel in channels}
    ):
        raise ValueError("Reviewed competition/channel catalogue entries required")
    home_id = await session.scalar(
        select(Club.id).where(Club.name == home.value, Club.is_active.is_(True))
    )
    away_id = await session.scalar(
        select(Club.id).where(Club.name == away.value, Club.is_active.is_(True))
    )
    unknown = sum(value.needs_review for value in [home, away, competition, *channels])
    return MatchInput(
        kickoff_at=item.kickoff_at,
        home_name_raw=item.home_name_raw,
        away_name_raw=item.away_name_raw,
        home_name_display=home.value,
        away_name_display=away.value,
        home_club_id=home_id,
        away_club_id=away_id,
        competition_id=competition_record.id,
        channel_ids=frozenset(channel_ids),
        needs_review=unknown > 0,
        unknown_terms=unknown,
    )


async def _scrape_pipeline(
    sessions: async_sessionmaker[AsyncSession],
    reader: ScheduleReader,
    *,
    reference_date: date,
    fallback: NameFallback | None = None,
    provider_key: str = "primary_schedule",
    delay: float = 0.5,
    run_id: int,
    started: datetime,
) -> tuple[int, str]:
    if delay < 0:
        raise ValueError("Request delay cannot be negative")
    async with sessions() as session:
        mappings = list(
            await session.scalars(
                select(ClubSourceMapping)
                .join(Club)
                .where(
                    ClubSourceMapping.provider_key == provider_key,
                    ClubSourceMapping.is_active.is_(True),
                    Club.is_active.is_(True),
                    Club.is_tracked.is_(True),
                )
                .order_by(ClubSourceMapping.club_id)
            )
        )
    sources = [("daily", None)] + [(f"club-{row.club_id}", row.source_url) for row in mappings]
    batches = []
    for index, (reference, url) in enumerate(sources):
        if index:
            await asyncio.sleep(delay)
        try:
            raw = (
                await reader.daily_schedule(reference_date=reference_date)
                if url is None
                else await reader.club_schedule(url, reference_date=reference_date)
            )
            async with sessions.begin() as session:
                prepared = tuple([await prepare_match(session, item, fallback) for item in raw])
            # The parsers do not certify a complete time window: never infer destructive coverage.
            batches.append(
                SourceBatch(reference=reference, provider_key=provider_key, matches=prepared)
            )
        except Exception:
            batches.append(
                SourceBatch(reference=reference, provider_key=provider_key, successful=False)
            )
    run_id = await persist_run(
        sessions, tuple(batches), observed_at=started, existing_run_id=run_id
    )
    async with sessions() as session:
        run = await session.get(ScrapeRun, run_id)
        assert run is not None
        return run_id, run.status


async def scrape_pipeline(
    sessions: async_sessionmaker[AsyncSession],
    reader: ScheduleReader,
    *,
    reference_date: date,
    fallback: NameFallback | None = None,
    provider_key: str = "primary_schedule",
    delay: float = 0.5,
    trigger: Literal["scheduled", "manual"] = "scheduled",
    job_id: int | None = None,
) -> tuple[int, str]:
    started = utc_now()
    async with sessions.begin() as session:
        run = ScrapeRun(trigger=trigger, started_at=started, status="running")
        session.add(run)
        await session.flush()
        run_id = run.id
        if job_id is not None:
            job = await session.get(ScrapeJob, job_id)
            if job is None or job.status != "running":
                raise ValueError("Manual job must be claimed before execution")
            job.run_id = run_id
    try:
        return await _scrape_pipeline(
            sessions,
            reader,
            reference_date=reference_date,
            fallback=fallback,
            provider_key=provider_key,
            delay=delay,
            run_id=run_id,
            started=started,
        )
    except BaseException:
        async with sessions.begin() as session:
            interrupted = await session.get(ScrapeRun, run_id)
            assert interrupted is not None
            interrupted.status = "failed"
            interrupted.finished_at = utc_now()
            interrupted.error_count += 1
            session.add(
                ScrapeRunEvent(
                    run_id=run_id,
                    stage="pipeline",
                    level="error",
                    error_type="PipelineInterrupted",
                    message="Pipeline interrupted or failed",
                )
            )
        raise
