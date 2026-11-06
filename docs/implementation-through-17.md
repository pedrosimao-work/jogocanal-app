# Implementation review: Issues #11–17

## Delivered behavior

- **#11:** seven Lisbon calendar days, midnight-to-midnight DST-safe bounds, chronological televised matches, stale-match exclusion, honest empty states and safe unavailable state.
- **#12:** desktop match table/mobile cards; instant accent-insensitive search across teams, competitions and channels; accessible result count; channel badges; source-confirmed live/postponed/finished states. A follow-up carries optional status values through parsing, normalisation and persistence. Missing source statuses never invent live play or a final result.
- **#13:** database-driven first/second-division directory, confirmed latest-season memberships, local crests and club-specific schedules linked by canonical IDs. Unknown/inactive clubs return 404.
- **#14:** `/api/v1/matches`, `/api/v1/clubs`, `/api/v1/clubs/{slug}/matches`, `/api/v1/health`, explicit Pydantic public response schemas, bounded pagination and database readiness checks.
- **#15:** CLI-only administrator creation, salted scrypt passwords, revocable eight-hour database sessions, CSRF checks, durable per-account/IP login throttling, production Secure host-prefixed cookies, no-store admin pages and protected routes. No default account or public registration.
- **#16:** protected scraper history, failures and unknown-term dashboard; durable manual jobs deduplicated by a database constraint; separate worker sharing the scheduled scraper lock; run linkage and interrupted-job recovery. No scraping inside an HTTP request.
- **#17:** Quem Somos, Termos e Condições, Política de Privacidade; global footer containing info@jogocanal.com and “Desenvolvido por pedrosimao.work”; PyCharm launch instructions in README.

## Technical decisions

FastAPI remains ASGI-first, with async database/network access and password hashing off the event loop. The frontend remains Jinja plus locally bundled Bootstrap, with small local JavaScript for filtering. Public DTOs exclude operational source URLs and provider metadata. All browser assets are local.

The worker is deliberately single-host and SQLite-backed. Manual and scheduled commands must share the same lock file. Sessions and job uniqueness are enforced by the database, not per-process memory. Two migrations add sessions/throttles and the unique active-job slot; existing valid data is retained.

The legal text describes known application behavior and links to the CNPD for rights information. Actual production operator/hosting/log-retention/email arrangements remain deployment inputs and were not fabricated.

## Verification

- 157 pytest tests passed; **91.23% coverage** in a fresh `.venv`.
- Ruff lint and formatting passed; mypy passed for 60 application source files.
- `pip check`: no broken requirements.
- Alembic upgrade, schema check, downgrade to base, re-upgrade and schema check passed on isolated databases.
- Local development database was backed up before applying the verified migrations; final schema check passed.
- Browser verified the actual styled homepage, mobile match cards at a 390px viewport, no horizontal page overflow, mobile navigation, club links, accent-insensitive search, result count, no-result feedback and clearing search. Populated cases used a separate synthetic database, not the user's development database.
- Browser console reported no errors on the real local homepage.
- Scan of Git-visible files for private configured source URLs/domains passed.

## Review boundaries

No production deployment or cron installation occurred. Live schedule-source compatibility/connectivity and production worker scheduling remain operational follow-up under **Issue #9**. The actual local agenda currently has no matches; no fictional schedules were inserted into it. The club directory is populated. Administrator creation remains an explicit local CLI action using the owner's chosen credentials.

A new ignored `.venv` replaces the need to use the broken legacy interpreter reference in `venv`; the old directory was preserved. Run the README's PyCharm commands from the repository root, then open `http://127.0.0.1:8000/`. Opening a source file or API documentation does not display the website.

## Changed files

The following is the complete file inventory relative to merged Issue #10 (`87ede1c`), including this review document:

- `README.md`
- `alembic/versions/a15_admin_sessions.py`
- `alembic/versions/a16_unique_active_job.py`
- `app/admin/auth.py`
- `app/admin/dashboard.py`
- `app/api/v1/routes.py`
- `app/commands/create_admin.py`
- `app/commands/scrape.py`
- `app/commands/work_scrape_jobs.py`
- `app/core/security_headers.py`
- `app/main.py`
- `app/models/__init__.py`
- `app/models/admin_session.py`
- `app/models/scrape.py`
- `app/schemas/ingestion.py`
- `app/schemas/public.py`
- `app/scraper/parsers.py`
- `app/scraper/schemas.py`
- `app/services/auth.py`
- `app/services/clubs.py`
- `app/services/ingestion.py`
- `app/services/jobs.py`
- `app/services/schedule.py`
- `app/services/scrape_pipeline.py`
- `app/static/css/app.css`
- `app/static/js/schedule.js`
- `app/templates/about.html`
- `app/templates/admin/dashboard.html`
- `app/templates/admin/home.html`
- `app/templates/admin/login.html`
- `app/templates/agenda.html`
- `app/templates/club_detail.html`
- `app/templates/clubs.html`
- `app/templates/components/footer.html`
- `app/templates/components/match_table.html`
- `app/templates/privacy.html`
- `app/templates/terms.html`
- `app/web/routes.py`
- `docs/implementation-through-17.md`
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/integration/test_database_schema.py`
- `tests/integration/test_match_persistence.py`
- `tests/integration/test_scrape_pipeline.py`
- `tests/routes/__init__.py`
- `tests/routes/test_admin_auth.py`
- `tests/routes/test_admin_jobs.py`
- `tests/routes/test_clubs.py`
- `tests/routes/test_information_pages.py`
- `tests/routes/test_public_api.py`
- `tests/routes/test_schedule_page.py`
- `tests/unit/test_job_worker.py`
- `tests/unit/test_match_status.py`
- `tests/unit/test_schedule_source.py`
