"""Opt-in preservation of literal source names; never promote an AI guess."""

import hashlib
import re
from typing import TypeVar, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.models.competition import Competition
from app.models.normalisation import NormalisationCache
from app.schemas.normalisation import NameContext
from app.services.normalisation import lookup_key

CatalogueModel = TypeVar("CatalogueModel", Competition, Channel)


async def discover_entry(
    session: AsyncSession,
    model: type[CatalogueModel],
    raw: str,
    context: NameContext,
) -> CatalogueModel:
    name = " ".join(raw.split())
    if not name or len(name) > 120:
        raise ValueError("Invalid source catalogue name")
    record = cast(
        CatalogueModel | None, await session.scalar(select(model).where(model.name == name))
    )
    if record is not None:
        if not record.is_active:
            raise ValueError("Source catalogue name is disabled")
        return record
    stem = re.sub(r"[^a-z0-9]+", "-", lookup_key(name)).strip("-")[:90] or "name"
    slug = stem + "-" + hashlib.sha256(name.encode()).hexdigest()[:12]
    record = model(name=name, slug=slug, is_active=True)
    session.add(record)
    key = lookup_key(name)
    review = await session.scalar(
        select(NormalisationCache).where(
            NormalisationCache.context == context, NormalisationCache.lookup_key == key
        )
    )
    if review is None:
        session.add(
            NormalisationCache(
                context=context,
                raw_value=name,
                lookup_key=key,
                normalized_value=name,
                resolution_method="rule",
                needs_review=True,
                use_count=1,
            )
        )
    await session.flush()
    return record
