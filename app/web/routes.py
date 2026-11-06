from datetime import date, datetime
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from app.db.dependencies import get_db_session
from app.services.clubs import club_directory, find_club
from app.services.schedule import lisbon_today, seven_day_schedule

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


def render(request: Request, page: str, title: str) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name=f"{page}.html",
        context={
            "page": page,
            "title": title,
            "year": datetime.now(ZoneInfo("Europe/Lisbon")).year,
        },
    )


@router.get("/", response_class=HTMLResponse, name="agenda")
async def agenda(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    today: Annotated[date, Depends(lisbon_today)],
) -> HTMLResponse:
    unavailable = False
    try:
        days = await seven_day_schedule(session, today)
    except SQLAlchemyError:
        days = []
        unavailable = True
    return templates.TemplateResponse(
        request=request,
        name="agenda.html",
        context={
            "page": "agenda",
            "title": "Futebol na televisão",
            "year": today.year,
            "days": days,
            "schedule_unavailable": unavailable,
        },
        status_code=503 if unavailable else 200,
    )


@router.get("/clubes", response_class=HTMLResponse, name="clubs")
async def clubs(
    request: Request, session: Annotated[AsyncSession, Depends(get_db_session)]
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="clubs.html",
        context={
            "page": "clubs",
            "title": "Clubes",
            "year": lisbon_today().year,
            "divisions": await club_directory(session),
        },
    )


@router.get("/clubes/{slug}", response_class=HTMLResponse, name="club_detail")
async def club_detail(
    request: Request,
    slug: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    today: Annotated[date, Depends(lisbon_today)],
) -> HTMLResponse:
    club = await find_club(session, slug)
    if club is None:
        raise HTTPException(404, "Clube não encontrado")
    days = await seven_day_schedule(session, today)
    for day in days:
        day.matches = [
            match for match in day.matches if club.id in (match.home_club_id, match.away_club_id)
        ]
    return templates.TemplateResponse(
        request=request,
        name="club_detail.html",
        context={
            "page": "clubs",
            "title": club.name,
            "year": today.year,
            "club": club,
            "days": days,
        },
    )


@router.get("/sobre", response_class=HTMLResponse, name="about")
async def about(request: Request) -> HTMLResponse:
    return render(request, "about", "Sobre o JogoCanal")
