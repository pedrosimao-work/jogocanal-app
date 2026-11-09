# Branding and local ingestion review — 9 November 2026

## Changes and decisions
- Original supplied logo in the header and six favicon/image assets; remove the generated mark.
- Main banner is a slim 90px desktop bar with headline left and agenda action right.
  Mobile stacks both compactly. Introductory copy and duplicate logo are removed.
- Orange #F68B3A, black/white, grey cards, Anton headings and Inter body text.
- Fonts and Bootstrap served locally. Original font licences included.
- Black text on orange buttons deliberately improves contrast over white text.
- Preserve ASGI FastAPI, Jinja and Bootstrap, with separate updater processes.
- HTTP client uses OS certificate trust; certificate and hostname checks remain enabled.
- Optional --discover-catalogue retains literal unknown competition/channel names,
  creates review entries and never promotes AI guesses into new identities.
  Existing strict CLI behavior remains the default; the local launcher opts in.
- Add agenda update timestamp and incomplete-update notice.
- Remove the isolated timezone label from navigation. Agenda, club schedules and
  accessible table captions specify Hora de Portugal Continental (Europe/Lisbon).
- Root run.py starts Uvicorn, immediate/periodic ingestion and manual-job polling.
  Updates run every 30 minutes after completion; manual jobs poll every 15 seconds.
  Occupied ports fail before updater startup. Shutdown terminates owned Windows
  child process trees. No production cron, deployment or schema change.

## Verification
- 163 pytest tests passed; 89.17% coverage (80% required).
- Ruff check and formatting passed; mypy passed for 62 app source files.
- git diff --check passed.
- Two real ingestion runs: 37/37 pages each, 1,061 observations each, zero errors.
  First run created 630 unique matches; repeat created zero duplicates.
- Seven-day agenda: 109 matches, including 19 with channel awaiting confirmation.
  Counts are a dated observation, not fixed expected future totals.
- Desktop and 390px mobile layout inspected; search, local fonts and images verified.
- Actual launcher startup and cancellation verified; released port rebound successfully.
- Database and private source configuration remain local and ignored by Git.
- Taça de Portugal check: no fixtures in the local database or current daily feed.
  The dedicated competition page lists historical broadcasts and no upcoming ones.
  The agenda does not filter out this competition, but live cup coverage is not yet
  verified with an upcoming fixture. Historical games are not added to the agenda.

## PyCharm review
1. Open this repository and select its .venv/Scripts/python.exe interpreter.
2. In the project terminal run `.\.venv\Scripts\python.exe run.py`, or right-click
   the root run.py and choose Run. Do not execute app/main.py directly.
3. Open http://127.0.0.1:8000/ and keep the terminal running.
4. Confirm original logo, orange branding, match rows and channels. Search for
   Portugal or Sport TV, open Clubes and resize the browser to check mobile cards.
5. Wait for the scrape completion message and refresh to see the updated timestamp.
6. Check http://127.0.0.1:8000/api/v1/health for database health.
7. Ctrl+C in the terminal stops services. A website-only review can use --no-scrape.

## Git review
Branch: codex/brand-and-live-schedule. Implementation approved for commit and push
on 9 November 2026 after visual review. No production deployment is included.
The list below includes this review file.

## Files changed
- `README.md`
- `app/commands/run_local.py`
- `app/commands/scrape.py`
- `app/commands/work_scrape_jobs.py`
- `app/scraper/client.py`
- `app/services/catalogue_discovery.py`
- `app/services/scrape_pipeline.py`
- `app/static/brand/android-chrome-192x192.png`
- `app/static/brand/android-chrome-512x512.png`
- `app/static/brand/apple-touch-icon.png`
- `app/static/brand/favicon-16x16.png`
- `app/static/brand/favicon-32x32.png`
- `app/static/brand/favicon.ico`
- `app/static/brand/mark.svg`
- `app/static/brand/site.webmanifest`
- `app/static/css/app.css`
- `app/static/fonts/Anton-OFL.txt`
- `app/static/fonts/Anton-Regular.ttf`
- `app/static/fonts/Inter-OFL.txt`
- `app/static/fonts/Inter-Variable.ttf`
- `app/static/fonts/README.md`
- `app/templates/about.html`
- `app/templates/admin/dashboard.html`
- `app/templates/admin/home.html`
- `app/templates/admin/login.html`
- `app/templates/agenda.html`
- `app/templates/base.html`
- `app/templates/club_detail.html`
- `app/templates/components/header.html`
- `app/templates/components/match_table.html`
- `app/web/routes.py`
- `docs/branding-live-review.md`
- `run.py`
- `tests/integration/test_scrape_pipeline.py`
- `tests/unit/test_run_local.py`
- `tests/unit/test_schedule_source.py`
