"""Public club directory; never expose operational source mappings."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.club import Club
from app.models.league import League, LeagueMembership


@dataclass(frozen=True)
class PublicClub:
    id: int
    name: str
    slug: str
    short_name: str
    crest_path: str | None


@dataclass
class ClubDivision:
    name: str
    season: str
    clubs: list[PublicClub]


def public_club(club: Club) -> PublicClub:
    crest = club.crest_path
    # Only repo-owned images are served; database data cannot introduce remote resources.
    if crest and (not crest.startswith("crests/") or ".." in crest or ":" in crest):
        crest = None
    return PublicClub(club.id, club.name, club.slug, club.short_name, crest)


async def club_directory(session: AsyncSession) -> list[ClubDivision]:
    latest = select(func.max(LeagueMembership.season)).scalar_subquery()
    rows = await session.execute(
        select(League, LeagueMembership, Club)
        .join(LeagueMembership, LeagueMembership.league_id == League.id)
        .join(Club, Club.id == LeagueMembership.club_id)
        .where(
            LeagueMembership.season == latest,
            LeagueMembership.is_confirmed.is_(True),
            League.tier.in_([1, 2]),
            League.is_active.is_(True),
            Club.is_active.is_(True),
            Club.is_tracked.is_(True),
        )
        .order_by(League.tier, League.id, LeagueMembership.display_order, Club.name)
    )
    groups: dict[int, ClubDivision] = {}
    for league, membership, club in rows:
        groups.setdefault(league.id, ClubDivision(league.name, membership.season, []))
        groups[league.id].clubs.append(public_club(club))
    return list(groups.values())


async def find_club(session: AsyncSession, slug: str) -> PublicClub | None:
    club = await session.scalar(
        select(Club).where(Club.slug == slug, Club.is_active.is_(True), Club.is_tracked.is_(True))
    )
    return public_club(club) if club else None
