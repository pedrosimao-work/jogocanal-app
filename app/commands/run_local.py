"""Local supervisor: ASGI server plus separate, lock-protected ingestion processes."""

import argparse
import asyncio
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def child_command(module: str, *arguments: str) -> list[str]:
    return [sys.executable, "-m", module, *arguments]


async def supervise(port: int, refresh: int, worker: int, no_scrape: bool = False) -> int:
    # Refuse an occupied port before any updater can start.
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            print(f"Port {port} is already in use. Stop the previous run or choose --port.")
            return 1
    children: set[asyncio.subprocess.Process] = set()

    async def run(command: list[str]) -> int:
        process = await asyncio.create_subprocess_exec(*command, cwd=ROOT)
        children.add(process)
        try:
            return await process.wait()
        finally:
            if process.returncode is not None:
                children.discard(process)

    async def periodic(module: str, interval: int) -> None:
        while True:
            code = await run(child_command(module, "--discover-catalogue"))
            if code not in (0, 75):
                print(f"Local updater exited with code {code}; retrying automatically.", flush=True)
            await asyncio.sleep(interval if code == 0 else min(interval, 60))

    server = asyncio.create_task(
        run(child_command("uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)))
    )
    tasks: list[asyncio.Task[int] | asyncio.Task[None]] = [server]
    try:
        # Let bind/startup errors surface before starting any source requests.
        await asyncio.sleep(1)
        if server.done():
            return await server
        if not no_scrape:
            tasks.extend(
                [
                    asyncio.create_task(periodic("app.commands.scrape", refresh)),
                    asyncio.create_task(periodic("app.commands.work_scrape_jobs", worker)),
                ]
            )
        print(
            f"Open http://127.0.0.1:{port}/ — keep this terminal open; Ctrl+C stops all local services.",
            flush=True,
        )
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            result = task.result()
            if result is not None:
                return result
        return 1
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for child in children:
            if child.returncode is None:
                if os.name == "nt":
                    # Windows venv executables spawn another Python process. Kill
                    # the owned process tree, not just its redirector executable.
                    killer = await asyncio.create_subprocess_exec(
                        "taskkill",
                        "/PID",
                        str(child.pid),
                        "/T",
                        "/F",
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await killer.wait()
                else:
                    child.terminate()
        for child in children:
            try:
                await asyncio.wait_for(child.wait(), timeout=5)
            except TimeoutError:
                child.kill()
                await child.wait()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local website and its schedule updater")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--refresh-seconds", type=int, default=1800)
    parser.add_argument("--worker-seconds", type=int, default=15)
    parser.add_argument(
        "--no-scrape", action="store_true", help="Website-only preview using saved matches"
    )
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535 or args.refresh_seconds < 60 or args.worker_seconds < 5:
        parser.error("port must be valid, refresh at least 60s and worker interval at least 5s")
    try:
        return asyncio.run(
            supervise(args.port, args.refresh_seconds, args.worker_seconds, args.no_scrape)
        )
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
