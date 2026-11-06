"""Persist source batches atomically and retain durable, source-neutral run records."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.channel import Channel
from app.models.club import Club
from app.models.competition import Competition
from app.models.match import Match, MatchChannel
from app.models.mixins import utc_now
from app.models.scrape import ScrapeRun, ScrapeRunEvent
from app.schemas.ingestion import MatchInput, SourceBatch
from app.services.normalisation import lookup_key


def _utc(value: datetime) -> datetime:
    # SQLite returns naive values for UTC DateTime columns.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def match_fingerprint(item: MatchInput, provider: str = "primary_schedule") -> str:
    identity = [
        provider,
        item.kickoff_at.astimezone(UTC).isoformat(),
        item.competition_id,
        f"club:{item.home_club_id}"
        if item.home_club_id
        else f"name:{lookup_key(item.home_name_display)}",
        f"club:{item.away_club_id}"
        if item.away_club_id
        else f"name:{lookup_key(item.away_name_display)}",
    ]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode("utf-8")).hexdigest()


async def _validate_catalogue(session: AsyncSession, item: MatchInput) -> None:
    if await session.get(Competition, item.competition_id) is None:
        raise ValueError("Unknown competition")
    for club_id in (item.home_club_id, item.away_club_id):
        if club_id is not None and await session.get(Club, club_id) is None:
            raise ValueError("Unknown club")
    channels = set(
        await session.scalars(select(Channel.id).where(Channel.id.in_(item.channel_ids)))
    )
    if channels != item.channel_ids:
        raise ValueError("Unknown channel")


async def _upsert(
    session: AsyncSession,
    item: MatchInput,
    provider: str,
    observed_at: datetime,
    merge_channels: bool,
) -> Literal["created", "updated", "unchanged"]:
    await _validate_catalogue(session, item)
    fingerprint = match_fingerprint(item, provider)
    record = (
        await session.scalars(select(Match).where(Match.fingerprint == fingerprint))
    ).one_or_none()
    created = record is None
    if record is not None:
        if _utc(record.last_seen_at) > observed_at:
            return "unchanged"
        if record.source_updated_at is not None and (
            item.source_updated_at is None
            or item.source_updated_at < _utc(record.source_updated_at)
        ):
            return "unchanged"
    if record is None:
        record = Match(
            fingerprint=fingerprint, kickoff_at=item.kickoff_at, first_seen_at=observed_at
        )
        session.add(record)
    record.home_club_id = item.home_club_id
    record.away_club_id = item.away_club_id
    record.home_name_raw = item.home_name_raw
    record.away_name_raw = item.away_name_raw
    record.home_name_display = item.home_name_display
    record.away_name_display = item.away_name_display
    record.competition_id = item.competition_id
    record.provider_key = provider
    record.source_updated_at = item.source_updated_at
    record.last_seen_at = observed_at
    record.is_stale = False
    record.needs_review = (
        item.needs_review or item.unknown_terms > 0 or (merge_channels and record.needs_review)
    )
    await session.flush()
    existing = set(
        await session.scalars(
            select(MatchChannel.channel_id).where(MatchChannel.match_id == record.id)
        )
    )
    desired = set(item.channel_ids) | existing if merge_channels else set(item.channel_ids)
    await session.execute(
        delete(MatchChannel).where(
            MatchChannel.match_id == record.id,
            MatchChannel.channel_id.not_in(desired),
        )
    )
    for channel_id in desired - existing:
        session.add(MatchChannel(match_id=record.id, channel_id=channel_id))
    await session.flush()
    return "created" if created else "updated"


async def persist_run(
    sessions: async_sessionmaker[AsyncSession],
    batches: tuple[SourceBatch, ...],
    *,
    trigger: Literal["scheduled", "manual"] = "scheduled",
    observed_at: datetime | None = None,
    existing_run_id: int | None = None,
) -> int:
    """Own transactions; return the durable run ID. Callers serialize ingestion runs."""
    observed_at = observed_at or utc_now()
    if observed_at.utcoffset() is None or trigger not in {"scheduled", "manual"}:
        raise ValueError("Invalid run metadata")
    observed_at = observed_at.astimezone(UTC)
    if len({batch.reference for batch in batches}) != len(batches):
        raise ValueError("Source references must be unique within a run")
    async with sessions.begin() as session:
        if existing_run_id is None:
            new_run = ScrapeRun(trigger=trigger, started_at=observed_at, status="running")
            session.add(new_run)
            await session.flush()
            run_id = new_run.id
        else:
            pending = await session.get(ScrapeRun, existing_run_id)
            if pending is None or pending.status != "running" or pending.sources_attempted:
                raise ValueError("Run is not available for persistence")
            run_id = existing_run_id
    seen: set[str] = set()
    successful: list[SourceBatch] = []
    for batch in batches:
        try:
            if not batch.successful:
                raise ValueError("Source failed")
            created = updated = unknown = 0
            batch_seen: set[str] = set()
            async with sessions.begin() as session:
                for item in batch.matches:
                    fingerprint = match_fingerprint(item, batch.provider_key)
                    outcome = await _upsert(
                        session,
                        item,
                        batch.provider_key,
                        observed_at,
                        fingerprint in seen or fingerprint in batch_seen,
                    )
                    created += outcome == "created"
                    updated += outcome == "updated" and fingerprint not in batch_seen
                    unknown += item.unknown_terms
                    batch_seen.add(fingerprint)
                run = await session.get(ScrapeRun, run_id)
                assert run is not None
                run.sources_attempted += 1
                run.sources_successful += 1
                run.matches_found += len(batch.matches)
                run.matches_created += created
                run.matches_updated += updated
                run.unknown_terms += unknown
                session.add(
                    ScrapeRunEvent(
                        run_id=run_id,
                        stage="persist",
                        level="info",
                        source_reference=batch.reference,
                        message="Source batch persisted",
                    )
                )
            seen.update(batch_seen)
            successful.append(batch)
        except Exception:
            # Persist safe diagnostics in a separate transaction after the source rollback.
            async with sessions.begin() as session:
                run = await session.get(ScrapeRun, run_id)
                assert run is not None
                run.sources_attempted += 1
                run.error_count += 1
                session.add(
                    ScrapeRunEvent(
                        run_id=run_id,
                        stage="persist",
                        level="error",
                        source_reference=batch.reference,
                        error_type="SourceBatchFailure",
                        message="Source batch failed; previous match data preserved",
                    )
                )
    async with sessions.begin() as session:
        for batch in successful:
            if not batch.complete or (not batch.matches and not batch.allow_empty):
                session.add(
                    ScrapeRunEvent(
                        run_id=run_id,
                        stage="stale",
                        level="warning",
                        source_reference=batch.reference,
                        message="Stale marking skipped: incomplete or unconfirmed empty coverage",
                    )
                )
                continue
            assert batch.window_start is not None and batch.window_end is not None
            query = select(Match).where(
                Match.provider_key == batch.provider_key,
                Match.kickoff_at >= max(batch.window_start, observed_at),
                Match.kickoff_at < batch.window_end,
                Match.last_seen_at < observed_at,
            )
            if batch.club_id is not None:
                query = query.where(
                    or_(Match.home_club_id == batch.club_id, Match.away_club_id == batch.club_id)
                )
            stale_count = 0
            for record in await session.scalars(query):
                if record.fingerprint not in seen:
                    stale_count += not record.is_stale
                    record.is_stale = True
            session.add(
                ScrapeRunEvent(
                    run_id=run_id,
                    stage="stale",
                    level="info",
                    source_reference=batch.reference,
                    message=f"Newly stale matches: {stale_count}",
                )
            )
        run = await session.get(ScrapeRun, run_id)
        assert run is not None
        run.status = (
            "completed"
            if run.error_count == 0
            else "partial"
            if run.sources_successful
            else "failed"
        )
        run.finished_at = utc_now()
        run.summary = (
            f"Sources: {run.sources_successful}/{run.sources_attempted}; errors: {run.error_count}"
        )
    return run_id
