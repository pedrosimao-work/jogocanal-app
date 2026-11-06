from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.schemas.public import DivisionResponse, MatchPage, PublicMatchResponse, ServiceHealth
from app.services.clubs import club_directory, find_club
from app.services.schedule import lisbon_today, seven_day_schedule

router = APIRouter(prefix="/api/v1", tags=["Public API"])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=10000)]
Start = Annotated[date | None, Query(ge=date(2000, 1, 1), le=date(2100, 12, 24))]


async def match_page(
    session: AsyncSession, start: date, limit: int, offset: int, club_id: int | None = None
) -> MatchPage:
    days = await seven_day_schedule(session, start)
    matches = [
        match
        for day in days
        for match in day.matches
        if club_id is None or club_id in (match.home_club_id, match.away_club_id)
    ]
    return MatchPage(
        start_date=start,
        total=len(matches),
        limit=limit,
        offset=offset,
        items=[
            PublicMatchResponse.model_validate(match) for match in matches[offset : offset + limit]
        ],
    )


@router.get("/matches", response_model=MatchPage)
async def matches(
    session: Session, start_date: Start = None, limit: Limit = 50, offset: Offset = 0
) -> MatchPage:
    return await match_page(session, start_date or lisbon_today(), limit, offset)


@router.get("/clubs", response_model=list[DivisionResponse])
async def clubs(session: Session) -> list[DivisionResponse]:
    return [DivisionResponse.model_validate(division) for division in await club_directory(session)]


@router.get("/clubs/{slug}/matches", response_model=MatchPage)
async def club_matches(
    slug: str, session: Session, start_date: Start = None, limit: Limit = 50, offset: Offset = 0
) -> MatchPage:
    club = await find_club(session, slug)
    if club is None:
        raise HTTPException(404, "Club not found")
    return await match_page(session, start_date or lisbon_today(), limit, offset, club.id)


@router.get("/health", response_model=ServiceHealth)
async def health(session: Session, response: Response) -> ServiceHealth:
    response.headers["Cache-Control"] = "no-store"
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = 503
        return ServiceHealth(status="unavailable", database="unavailable")
    return ServiceHealth(status="ok", database="ok")
