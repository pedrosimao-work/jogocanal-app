"""Run with python -m app.commands.scrape; never run scraping inside an HTTP request."""

import argparse
import asyncio
import math
from contextlib import AsyncExitStack
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.core.scrape_lock import ScraperAlreadyRunning, scraper_lock


async def execute(args: argparse.Namespace) -> int:
    # Delay configuration imports so startup errors are handled without leaking values.
    from app.core.config import settings
    from app.db.session import async_session_factory, engine
    from app.scraper.client import ScheduleSourceClient
    from app.scraper.config import load_schedule_source_config
    from app.services.groq_normalisation import GroqNormaliser
    from app.services.scrape_pipeline import scrape_pipeline

    try:
        config = load_schedule_source_config(args.config)
        async with AsyncExitStack() as stack:
            client = await stack.enter_async_context(ScheduleSourceClient(config))
            fallback = None
            if settings.groq_api_key is not None or settings.groq_model is not None:
                if settings.groq_api_key is None or settings.groq_model is None:
                    raise ValueError("Both Groq settings are required")
                fallback = await stack.enter_async_context(
                    GroqNormaliser(settings.groq_api_key, settings.groq_model)
                )
            async with asyncio.timeout(args.timeout):
                run_id, status = await scrape_pipeline(
                    async_session_factory,
                    client,
                    reference_date=datetime.now(ZoneInfo("Europe/Lisbon")).date(),
                    fallback=fallback,
                    delay=args.delay,
                    trigger=args.trigger,
                    job_id=getattr(args, "job_id", None),
                )
            print(f"Scrape run {run_id}: {status}")
            return {"completed": 0, "partial": 3, "failed": 1}[status]
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the JogoCanal schedule ingestion pipeline.")
    parser.add_argument("--config", type=Path, default=Path("private/schedule_source.json"))
    parser.add_argument("--lock-file", type=Path, default=Path("private/scraper.lock"))
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--trigger", choices=("scheduled", "manual"), default="scheduled")
    args = parser.parse_args(argv)
    if (
        not math.isfinite(args.timeout)
        or not math.isfinite(args.delay)
        or args.timeout <= 0
        or args.delay < 0
    ):
        parser.error("timeout must be positive and delay must be nonnegative")
    try:
        with scraper_lock(args.lock_file.resolve()):
            return asyncio.run(execute(args))
    except ScraperAlreadyRunning:
        print("Scrape skipped: another process holds the execution lock")
        return 75
    except KeyboardInterrupt:
        print("Scrape interrupted")
        return 130
    except Exception:
        print("Scrape failed: check private configuration, database and source connectivity")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
