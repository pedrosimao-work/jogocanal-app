from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

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
async def agenda(request: Request) -> HTMLResponse:
    return render(request, "agenda", "Futebol na televisão")


@router.get("/clubes", response_class=HTMLResponse, name="clubs")
async def clubs(request: Request) -> HTMLResponse:
    return render(request, "clubs", "Clubes")


@router.get("/sobre", response_class=HTMLResponse, name="about")
async def about(request: Request) -> HTMLResponse:
    return render(request, "about", "Sobre o JogoCanal")
