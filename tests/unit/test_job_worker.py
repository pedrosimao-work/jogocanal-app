from app.commands import work_scrape_jobs
from app.core.scrape_lock import ScraperAlreadyRunning


def test_worker_cli_lock_and_error_redaction(monkeypatch, tmp_path, capsys):
    async def fail(args):
        raise RuntimeError("private-secret")

    monkeypatch.setattr(work_scrape_jobs, "execute", fail)
    assert work_scrape_jobs.main(["--lock-file", str(tmp_path / "lock")]) == 1
    assert "private-secret" not in capsys.readouterr().out

    def locked(path):
        raise ScraperAlreadyRunning()

    monkeypatch.setattr(work_scrape_jobs, "scraper_lock", locked)
    assert work_scrape_jobs.main([]) == 75
