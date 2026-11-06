"""Deterministic names first, then persistent cache and optional AI suggestions."""

import re
import unicodedata
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.models.club import Club, ClubAlias
from app.models.competition import Competition
from app.models.mixins import utc_now
from app.models.normalisation import NormalisationCache
from app.schemas.normalisation import NameContext, NormalisedName


def lookup_key(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^\w\s+]", " ", value).replace("_", " ").split())


class NameFallback(Protocol):
    model: str

    async def suggest(self, context: NameContext, raw: str) -> str | None: ...


class NameNormaliser:
    """Caller owns the session transaction and commits cache writes explicitly."""

    def __init__(self, session: AsyncSession, fallback: NameFallback | None = None) -> None:
        self.session = session
        self.fallback = fallback

    async def _deterministic(self, context: NameContext, key: str) -> NormalisedName | None:
        candidates: set[str] = set()
        if context == "club":
            aliases = await self.session.execute(
                select(ClubAlias.normalized_alias, Club.name)
                .join(Club, Club.id == ClubAlias.club_id)
                .where(Club.is_active.is_(True))
            )
            candidates.update(name for alias, name in aliases if lookup_key(alias) == key)
        models: dict[NameContext, type[Club] | type[Competition] | type[Channel]] = {
            "club": Club,
            "competition": Competition,
            "channel": Channel,
        }
        model = models[context]
        records = await self.session.scalars(select(model).where(model.is_active.is_(True)))
        for record in records:
            assert isinstance(record, (Club, Competition, Channel))
            variants = [record.name, record.slug]
            if isinstance(record, Club):
                variants.append(record.short_name)
            if any(lookup_key(value) == key for value in variants):
                candidates.add(record.name)
        if len(candidates) == 1:
            return NormalisedName(candidates.pop(), "alias" if context == "club" else "rule", False)
        return None

    async def _cached(self, context: NameContext, key: str) -> NormalisationCache | None:
        result = await self.session.scalars(
            select(NormalisationCache).where(
                NormalisationCache.context == context,
                NormalisationCache.lookup_key == key,
            )
        )
        return result.one_or_none()

    async def _reuse(self, entry: NormalisationCache) -> NormalisedName:
        result = NormalisedName(
            entry.normalized_value, entry.resolution_method, entry.needs_review, True
        )
        await self.session.execute(
            update(NormalisationCache)
            .where(NormalisationCache.id == entry.id)
            .values(use_count=NormalisationCache.use_count + 1, last_used_at=utc_now())
        )
        return result

    async def normalise(self, raw: str, context: NameContext) -> NormalisedName:
        raw = " ".join(raw.split())
        if context not in {"club", "competition", "channel"} or not raw or len(raw) > 255:
            raise ValueError("Invalid normalisation input")
        key = lookup_key(raw)
        if not key or len(key) > 255:
            raise ValueError("Invalid normalisation lookup key")
        cached = await self._cached(context, key)
        if cached is not None and cached.resolution_method == "manual":
            return await self._reuse(cached)
        deterministic = await self._deterministic(context, key)
        if deterministic is not None:
            return deterministic
        if cached is not None:
            return await self._reuse(cached)
        if self.fallback is None:
            return NormalisedName(raw, "unresolved", True)
        suggestion = await self.fallback.suggest(context, raw)
        limit = 160 if context == "competition" else 120
        if suggestion is None or not suggestion.strip() or len(suggestion) > limit:
            return NormalisedName(raw, "unresolved", True)
        suggestion = " ".join(suggestion.split())
        entry = NormalisationCache(
            context=context,
            raw_value=raw,
            lookup_key=key,
            normalized_value=suggestion,
            resolution_method="groq",
            model_name=self.fallback.model,
            needs_review=True,
            use_count=1,
            last_used_at=utc_now(),
        )
        self.session.add(entry)
        await self.session.flush()
        return NormalisedName(suggestion, "groq", True)
