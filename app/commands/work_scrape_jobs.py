"""Process one durable manual update; invoke every minute alongside the scheduled scrape."""

import argparse
import asyncio
import math
from pathlib import Path

from app.core.scrape_lock import ScraperAlreadyRunning, scraper_lock


async def execute(args: argparse.Namespace) -> int:
    from app.commands.scrape import execute as scrape
    from app.db.session import async_session_factory, engine
    from app.services.jobs import process_one

    async def run(job_id: int) -> int:
        args.job_id = job_id
        args.trigger = "manual"
        return await scrape(args)

    try:
        return await process_one(async_session_factory, run)
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Process one queued manual schedule update")
    parser.add_argument("--config", type=Path, default=Path("private/schedule_source.json"))
    parser.add_argument("--lock-file", type=Path, default=Path("private/scraper.lock"))
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--discover-catalogue", action="store_true")
    args = parser.parse_args(argv)
    if (
        not math.isfinite(args.timeout)
        or args.timeout <= 0
        or not math.isfinite(args.delay)
        or args.delay < 0
    ):
        parser.error("timeout must be positive and delay nonnegative")
    try:
        with scraper_lock(args.lock_file.resolve()):
            return asyncio.run(execute(args))
    except ScraperAlreadyRunning:
        print("Worker skipped: scraper already running; queued request retained")
        return 75
    except KeyboardInterrupt:
        return 130
    except Exception:
        print("Worker failed; inspect the administration history and private configuration")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
