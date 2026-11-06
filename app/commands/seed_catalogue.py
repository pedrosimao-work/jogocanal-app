"""Import operator-reviewed competition and channel names before scraping."""

import argparse
import asyncio
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.models.competition import Competition


class CatalogueEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class Catalogue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    competitions: list[CatalogueEntry]
    channels: list[CatalogueEntry]


async def seed_catalogue(session: AsyncSession, catalogue: Catalogue) -> None:
    for model, entries in ((Competition, catalogue.competitions), (Channel, catalogue.channels)):
        if len({item.slug for item in entries}) != len(entries) or len(
            {item.name for item in entries}
        ) != len(entries):
            raise ValueError("Duplicate catalogue entries")
        for item in entries:
            record = (
                await session.scalars(select(model).where(model.slug == item.slug))
            ).one_or_none()
            if record is None:
                session.add(model(name=item.name, slug=item.slug, is_active=True))
            else:
                assert isinstance(record, (Competition, Channel))
                record.name = item.name
                record.is_active = True
    await session.flush()


async def _run(path: Path) -> None:
    from app.db.session import async_session_factory, engine

    try:
        catalogue = Catalogue.model_validate_json(path.read_text(encoding="utf-8-sig"))
        async with async_session_factory.begin() as session:
            await seed_catalogue(session, catalogue)
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Import an operator-reviewed name catalogue.")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        asyncio.run(_run(args.path))
    except Exception:
        print("Catalogue import failed; check private input and database configuration")
        return 1
    print("Reviewed catalogue imported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
