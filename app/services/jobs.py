"""Durable single-host queue. Worker processing requires the shared scraper lock."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.scrape import ScrapeJob, ScrapeRun


async def enqueue(session: AsyncSession, admin_id: int) -> int:
    existing = await session.scalar(select(ScrapeJob.id).where(ScrapeJob.active_slot == 1))
    if existing is not None:
        return existing
    job = ScrapeJob(status="pending", active_slot=1, requested_by_admin_id=admin_id)
    session.add(job)
    try:
        await session.commit()
        return job.id
    except IntegrityError:
        await session.rollback()
        winner = await session.scalar(select(ScrapeJob.id).where(ScrapeJob.active_slot == 1))
        if winner is None:
            raise
        return winner


async def process_one(
    sessions: async_sessionmaker[AsyncSession], runner: Callable[[int], Awaitable[int]]
) -> int:
    """Caller holds the same OS lock used by cron, including during crash recovery."""
    now = datetime.now(UTC)
    async with sessions.begin() as session:
        interrupted = list(
            await session.scalars(select(ScrapeJob).where(ScrapeJob.status == "running"))
        )
        for job in interrupted:
            job.status, job.active_slot, job.finished_at = "failed", None, now
            job.error_message = "Worker interrupted; request a new update."
            if job.run_id:
                run = await session.get(ScrapeRun, job.run_id)
                if run and run.status == "running":
                    run.status, run.finished_at = "failed", now
                    run.error_count += 1
        await session.flush()
        job_id = await session.scalar(
            select(ScrapeJob.id)
            .where(ScrapeJob.status == "pending")
            .order_by(ScrapeJob.id)
            .limit(1)
        )
        if job_id is None:
            return 0
        await session.execute(
            update(ScrapeJob).where(ScrapeJob.id == job_id).values(status="running", started_at=now)
        )
    code = 1
    try:
        code = await runner(job_id)
        return code
    finally:
        async with sessions.begin() as session:
            await session.execute(
                update(ScrapeJob)
                .where(ScrapeJob.id == job_id)
                .values(
                    status="completed" if code == 0 else "failed",
                    active_slot=None,
                    finished_at=datetime.now(UTC),
                    error_message=None
                    if code == 0
                    else "Update failed or incomplete; inspect run history.",
                )
            )
