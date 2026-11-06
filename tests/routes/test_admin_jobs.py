import asyncio
from datetime import UTC, date, datetime

import pytest
import pytest_asyncio
from bs4 import BeautifulSoup
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.commands.create_admin import create_admin
from app.models import metadata
from app.models.scrape import ScrapeJob, ScrapeRun
from app.services.jobs import enqueue, process_one
from app.services.scrape_pipeline import scrape_pipeline
from tests.routes.test_admin_auth import PASSWORD, login


@pytest_asyncio.fixture
async def jobs_factory(tmp_path):
    engine = create_async_engine("sqlite+aiosqlite:///" + (tmp_path / "jobs.db").as_posix())
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await create_admin(session, "admin@example.invalid", PASSWORD)
    yield factory
    await engine.dispose()


async def test_concurrent_enqueue_reserves_one_job(jobs_factory):
    async def request():
        async with jobs_factory() as session:
            return await enqueue(session, 1)

    ids = await asyncio.gather(request(), request(), request())
    assert len(set(ids)) == 1
    async with jobs_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ScrapeJob)) == 1


async def test_worker_links_run_and_releases_slot(jobs_factory):
    async with jobs_factory() as session:
        job_id = await enqueue(session, 1)

    class Reader:
        async def daily_schedule(self, *, reference_date):
            return ()

        async def club_schedule(self, url, *, reference_date):
            return ()

    async def run(job_id):
        _, status = await scrape_pipeline(
            jobs_factory, Reader(), reference_date=date.today(), trigger="manual", job_id=job_id
        )
        return 0 if status == "completed" else 1

    assert await process_one(jobs_factory, run) == 0
    async with jobs_factory() as session:
        job = await session.get(ScrapeJob, job_id)
        assert job.status == "completed" and job.active_slot is None
        assert job.run_id and job.finished_at
        assert (await session.get(ScrapeRun, job.run_id)).trigger == "manual"
        assert await enqueue(session, 1) != job_id


async def test_worker_failure_and_interrupted_recovery(jobs_factory):
    async with jobs_factory() as session:
        job_id = await enqueue(session, 1)

    async def fail(job_id):
        raise RuntimeError("private-source-secret")

    with pytest.raises(RuntimeError):
        await process_one(jobs_factory, fail)
    async with jobs_factory() as session:
        job = await session.get(ScrapeJob, job_id)
        assert job.status == "failed" and job.active_slot is None
        assert "secret" not in job.error_message
        next_id = await enqueue(session, 1)
        job = await session.get(ScrapeJob, next_id)
        run = ScrapeRun(trigger="manual", status="running")
        session.add(run)
        await session.flush()
        job.status, job.started_at, job.run_id = "running", datetime.now(UTC), run.id
        await session.commit()
    assert await process_one(jobs_factory, fail) == 0
    async with jobs_factory() as session:
        job = await session.get(ScrapeJob, next_id)
        assert job.status == "failed" and job.active_slot is None
        assert (await session.get(ScrapeRun, job.run_id)).status == "failed"


async def test_dashboard_and_manual_update_are_protected(client, web_session):
    assert (await client.get("/admin/scraper")).status_code == 303
    assert (await client.post("/admin/scraper/update", data={})).status_code == 303
    await create_admin(web_session, "admin@example.invalid", PASSWORD)
    await login(client)
    page = await client.get("/admin/scraper")
    assert page.status_code == 200 and "Sem termos pendentes" in page.text
    csrf = BeautifulSoup(page.text, "html.parser").select_one("[name=csrf]")["value"]
    assert (await client.post("/admin/scraper/update", data={"csrf": "bad"})).status_code == 403
    for _ in range(2):
        assert (await client.post("/admin/scraper/update", data={"csrf": csrf})).status_code == 303
    jobs = (await web_session.scalars(select(ScrapeJob))).all()
    assert len(jobs) == 1 and jobs[0].status == "pending"
    page = await client.get("/admin/scraper")
    assert BeautifulSoup(page.text, "html.parser").select_one("button[disabled]")


async def test_worker_command_processes_durable_job(jobs_factory, monkeypatch, tmp_path):
    import argparse
    from unittest.mock import AsyncMock

    from app.commands import scrape, work_scrape_jobs
    from app.db import session as database

    async with jobs_factory() as session:
        job_id = await enqueue(session, 1)
    seen = []

    async def run(args):
        seen.append((args.job_id, args.trigger))
        return 0

    monkeypatch.setattr(database, "async_session_factory", jobs_factory)
    monkeypatch.setattr(database, "engine", AsyncMock())
    monkeypatch.setattr(scrape, "execute", run)
    assert await work_scrape_jobs.execute(argparse.Namespace()) == 0
    assert seen == [(job_id, "manual")]
