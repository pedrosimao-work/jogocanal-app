import asyncio
import socket
from unittest.mock import AsyncMock

import pytest

from app.commands.run_local import child_command, main, supervise


async def test_supervisor_stops_children_when_server_exits(monkeypatch):
    class Process:
        def __init__(self, code=None):
            self.returncode = code
            self.stopped = False

        async def wait(self):
            if self.returncode is None:
                await asyncio.Event().wait()
            return self.returncode

        def terminate(self):
            self.stopped = True
            self.returncode = 0

    server = Process(1)
    spawn = AsyncMock(return_value=server)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    original_sleep = asyncio.sleep

    async def fast_sleep(_):
        await original_sleep(0)

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)
    assert await supervise(0, 1800, 15) == 1
    assert spawn.await_count == 1


def test_launcher_commands_and_invalid_frequency():
    assert child_command("app.commands.scrape")[-2:] == ["-m", "app.commands.scrape"]
    with pytest.raises(SystemExit):
        main(["--refresh-seconds", "1"])


async def test_occupied_port_does_not_start_workers(monkeypatch):
    spawn = AsyncMock()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        assert await supervise(occupied.getsockname()[1], 1800, 15) == 1
    spawn.assert_not_called()
