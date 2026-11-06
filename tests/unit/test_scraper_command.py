import subprocess
import sys
from pathlib import Path

import pytest

from app.commands import scrape
from app.core.scrape_lock import ScraperAlreadyRunning, scraper_lock


def test_lock_excludes_another_process_and_releases(tmp_path: Path) -> None:
    path = tmp_path / "scraper.lock"
    code = (
        "from pathlib import Path; from app.core.scrape_lock import scraper_lock; "
        "import sys; "
        "\nwith scraper_lock(Path(sys.argv[1])): print('acquired')"
    )
    with scraper_lock(path):
        result = subprocess.run(
            [sys.executable, "-c", code, str(path)], capture_output=True, timeout=10
        )
        assert result.returncode != 0
        assert b"acquired" not in result.stdout
    result = subprocess.run(
        [sys.executable, "-c", code, str(path)], capture_output=True, timeout=10
    )
    assert result.returncode == 0 and b"acquired" in result.stdout


def test_lock_released_after_exception(tmp_path: Path) -> None:
    with pytest.raises(ValueError), scraper_lock(tmp_path / "lock"):
        raise ValueError("test")
    with scraper_lock(tmp_path / "lock"):
        pass


@pytest.mark.parametrize("code", [0, 1, 3])
def test_command_returns_pipeline_exit_code(monkeypatch, tmp_path: Path, code: int) -> None:
    async def execute(args) -> int:
        return code

    monkeypatch.setattr(scrape, "execute", execute)
    assert scrape.main(["--lock-file", str(tmp_path / "lock")]) == code


def test_command_lock_contention(monkeypatch, tmp_path: Path) -> None:
    def locked(path):
        raise ScraperAlreadyRunning()

    monkeypatch.setattr(scrape, "scraper_lock", locked)
    assert scrape.main(["--lock-file", str(tmp_path / "lock")]) == 75


def test_command_failure_redacts_details(monkeypatch, tmp_path: Path, capsys) -> None:
    async def execute(args) -> int:
        raise RuntimeError("sensitive configuration")

    monkeypatch.setattr(scrape, "execute", execute)
    assert scrape.main(["--lock-file", str(tmp_path / "lock")]) == 1
    assert "sensitive" not in capsys.readouterr().out


def test_invalid_command_arguments() -> None:
    with pytest.raises(SystemExit) as error:
        scrape.main(["--timeout", "0"])
    assert error.value.code == 2
