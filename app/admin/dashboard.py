from datetime import UTC, datetime

from fastapi import APIRouter, Request
from sqlalchemy import select
from starlette.responses import HTMLResponse, RedirectResponse

from app.admin.auth import Admin, Session, check_csrf, cookie_name, read_form
from app.models.normalisation import NormalisationCache
from app.models.scrape import ScrapeJob, ScrapeRun, ScrapeRunEvent
from app.services.auth import digest
from app.services.jobs import enqueue
from app.web.routes import templates

router = APIRouter(prefix="/admin/scraper", include_in_schema=False)


@router.get("", name="scraper_dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: Session, admin: Admin) -> HTMLResponse:
    runs = list(await session.scalars(select(ScrapeRun).order_by(ScrapeRun.id.desc()).limit(20)))
    jobs = list(await session.scalars(select(ScrapeJob).order_by(ScrapeJob.id.desc()).limit(20)))
    events = list(
        await session.scalars(
            select(ScrapeRunEvent)
            .where(ScrapeRunEvent.level != "info")
            .order_by(ScrapeRunEvent.id.desc())
            .limit(30)
        )
    )
    unknown = list(
        await session.scalars(
            select(NormalisationCache)
            .where(NormalisationCache.needs_review.is_(True))
            .order_by(NormalisationCache.id.desc())
            .limit(50)
        )
    )
    active = await session.scalar(select(ScrapeJob.id).where(ScrapeJob.active_slot == 1))
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "title": "Atualizações",
            "page": "admin",
            "year": datetime.now(UTC).year,
            "runs": runs,
            "jobs": jobs,
            "events": events,
            "unknown": unknown,
            "active": active,
            "csrf": digest("csrf:" + request.cookies[cookie_name("session")]),
        },
    )


@router.post("/update", name="scraper_update")
async def manual_update(request: Request, session: Session, admin: Admin) -> RedirectResponse:
    form = await read_form(request)
    check_csrf(request, form)
    await enqueue(session, admin.id)
    return RedirectResponse(request.url_for("scraper_dashboard"), status_code=303)
