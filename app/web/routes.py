from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from app.db.dependencies import get_db_session
from app.models.scrape import ScrapeRun
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
    last_update = None
    refresh_incomplete = False
    try:
        days = await seven_day_schedule(session, today)
        latest = await session.scalar(select(ScrapeRun).order_by(ScrapeRun.id.desc()).limit(1))
        successful = await session.scalar(
            select(ScrapeRun)
            .where(ScrapeRun.status.in_(["completed", "partial"]))
            .order_by(ScrapeRun.id.desc())
            .limit(1)
        )
        if successful and successful.finished_at:
            stamp = successful.finished_at
            last_update = (stamp.replace(tzinfo=UTC) if stamp.tzinfo is None else stamp).astimezone(
                ZoneInfo("Europe/Lisbon")
            )
        refresh_incomplete = latest is not None and latest.status in {"partial", "failed"}
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
            "last_update": last_update,
            "refresh_incomplete": refresh_incomplete,
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


@router.get("/quem-somos", response_class=HTMLResponse, name="who_we_are")
async def who_we_are(request: Request) -> HTMLResponse:
    return render(request, "about", "Quem Somos")


@router.get("/termos-e-condicoes", response_class=HTMLResponse, name="terms")
async def terms(request: Request) -> HTMLResponse:
    return render(request, "terms", "Termos e Condições")


@router.get("/politica-de-privacidade", response_class=HTMLResponse, name="privacy")
async def privacy(request: Request) -> HTMLResponse:
    return render(request, "privacy", "Política de Privacidade")
