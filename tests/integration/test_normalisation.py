from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.commands.seed_reference_data import seed_reference_data
from app.data.reference import ALIAS_SEEDS, CLUB_SEEDS_BY_SLUG
from app.models import metadata
from app.models.channel import Channel
from app.models.competition import Competition
from app.models.normalisation import NormalisationCache
from app.schemas.normalisation import NameContext
from app.services.normalisation import NameNormaliser


class FakeFallback:
    model = "test-model"

    def __init__(self, answer: str | None = "Example FC") -> None:
        self.calls = 0
        self.answer = answer

    async def suggest(self, context: NameContext, raw: str) -> str | None:
        self.calls += 1
        return self.answer


async def test_cache_writes_respect_caller_rollback(session: AsyncSession) -> None:
    await NameNormaliser(session, FakeFallback()).normalise("Unknown", "club")
    await session.rollback()
    assert await session.scalar(select(func.count()).select_from(NormalisationCache)) == 0


async def test_deterministic_alias_overrides_old_ai_cache(session: AsyncSession) -> None:
    session.add(
        NormalisationCache(
            context="club",
            raw_value="Benfica",
            lookup_key="benfica",
            normalized_value="Old guess",
            resolution_method="groq",
            needs_review=True,
        )
    )
    await session.flush()
    result = await NameNormaliser(session).normalise("Benfica", "club")
    assert result.value == "SL Benfica" and not result.needs_review and not result.cached


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as value:
            await seed_reference_data(value)
            yield value
    finally:
        await engine.dispose()


async def test_all_seeded_aliases_resolve_without_ai(session: AsyncSession) -> None:
    fallback = FakeFallback()
    service = NameNormaliser(session, fallback)
    for alias in ALIAS_SEEDS:
        result = await service.normalise(alias.alias, "club")
        assert result.value == CLUB_SEEDS_BY_SLUG[alias.club_slug].name
        assert not result.needs_review
    assert fallback.calls == 0
    assert (await service.normalise("Benfica B", "club")).value != (
        await service.normalise("Benfica", "club")
    ).value


async def test_canonical_competition_and_channel_rules(session: AsyncSession) -> None:
    session.add_all(
        [
            Channel(name="SPORT TV 2", slug="sport-tv-2"),
            Competition(name="Taça de Portugal", slug="taca-de-portugal"),
        ]
    )
    await session.flush()
    fallback = FakeFallback()
    service = NameNormaliser(session, fallback)
    assert (await service.normalise("sport-tv-2", "channel")).value == "SPORT TV 2"
    assert (await service.normalise("TACA DE PORTUGAL", "competition")).value == "Taça de Portugal"
    assert fallback.calls == 0


async def test_fallback_cached_across_sessions_and_scoped_by_context(session: AsyncSession) -> None:
    fallback = FakeFallback()
    result = await NameNormaliser(session, fallback).normalise("Unknown", "club")
    assert result.needs_review and result.method == "groq" and not result.cached
    await session.commit()
    async with AsyncSession(session.bind, expire_on_commit=False) as second:
        result = await NameNormaliser(second, fallback).normalise("UNKNOWN", "club")
        assert result.cached and result.value == "Example FC"
        assert fallback.calls == 1
        await NameNormaliser(second, fallback).normalise("Unknown", "competition")
        assert fallback.calls == 2
        entry = await second.scalar(
            select(NormalisationCache).where(NormalisationCache.context == "club")
        )
        assert entry is not None and entry.use_count == 2 and entry.last_used_at is not None
        await second.commit()


async def test_manual_override_precedes_rules(session: AsyncSession) -> None:
    session.add(
        NormalisationCache(
            context="club",
            raw_value="Benfica",
            lookup_key="benfica",
            normalized_value="Reviewed Benfica",
            resolution_method="manual",
            needs_review=False,
        )
    )
    await session.flush()
    result = await NameNormaliser(session, FakeFallback()).normalise("Benfica", "club")
    assert result.value == "Reviewed Benfica" and not result.needs_review


@pytest.mark.parametrize("answer", [None, "", "X" * 121])
async def test_unresolved_input_not_cached(session: AsyncSession, answer: str | None) -> None:
    result = await NameNormaliser(session, FakeFallback(answer)).normalise("Unknown", "club")
    assert result.value == "Unknown" and result.needs_review and result.method == "unresolved"
    assert await session.scalar(select(func.count()).select_from(NormalisationCache)) == 0


async def test_disabled_fallback(session: AsyncSession) -> None:
    result = await NameNormaliser(session).normalise("Unlisted FC", "club")
    assert result.method == "unresolved" and result.needs_review


@pytest.mark.parametrize("raw", ["", "   ", "!!!", "x" * 256])
async def test_invalid_names(session: AsyncSession, raw: str) -> None:
    with pytest.raises(ValueError):
        await NameNormaliser(session).normalise(raw, "club")
