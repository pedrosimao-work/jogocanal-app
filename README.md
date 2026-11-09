# jogocanal-app
FastAPI application for discovering where and when football matches are broadcast in Portugal.

## Run locally in PyCharm

Open the repository folder in PyCharm. Use Python 3.11 and select
`.venv/Scripts/python.exe` as the project interpreter on Windows. If that environment
has not been created yet, run `python -m venv .venv`, then
`.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`.

From the repository root in the PyCharm PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.commands.seed_reference_data
.\.venv\Scripts\python.exe run.py
```

Alternatively, right-click root `run.py` in PyCharm and choose **Run** (not `app/main.py`).
The launcher starts the website, an immediate schedule update, updates every 30
minutes after completion, and a separate manual-job worker polling every 15 seconds.
Keep that terminal running and open **http://127.0.0.1:8000/** in your browser.
The interface is rendered by FastAPI with Jinja and locally bundled Bootstrap.
Opening a template file, GitHub source link or `/docs` does not show the website.
Use `/clubes` for the directory and `/admin/login` for administration. Press Ctrl+C
in the terminal to stop the server. No deployment is needed for this local review.

A new database contains clubs but no invented fixtures. The agenda accurately shows
empty days until an actual source update succeeds. The scraper and worker use the
private configuration described below. `run.py` enables literal catalogue discovery
so an empty competition/channel catalogue can be populated from source names,
with a normalisation review entry. It never creates identities from AI guesses.
Starting Uvicorn directly starts only the website. `run.py --no-scrape` is a
website-only preview of saved data. No operating-system scheduled job is installed.

To check locally: confirm the orange/black logo and styled agenda, search for a
team or channel, open `/clubes`, and check `/api/v1/health`. After an update finishes,
refresh the agenda to see its updated timestamp. Counts depend on current source
data; pending channels remain explicitly labelled. Ctrl+C stops local services.

## Reference data (2026/2027)

The seed contains 36 clubs, two leagues, 36 season memberships and 79 aliases.
There are 33 local crest images; the three B teams reuse their parent clubs' crests.

With Python 3.11 and an activated virtual environment, install dependencies and
prepare the database configured by `JOGOCANAL_DATABASE_URL` (local SQLite by default):

```console
python -m pip install -r requirements-dev.txt
python -m alembic upgrade head
python -m app.commands.seed_reference_data
```

To include private source mappings, copy `private/source_mappings.example.json` to
`private/source_mappings.json`. The example uses a real canonical club slug but a
non-working placeholder URL. Add an entry for each tracked club, using slugs from
`app/data/reference.py`. Replace the source identifier, URL and verification date
with privately verified values; keep the generic `primary_schedule` provider key.
Do not overwrite an existing private configuration when copying the example.

```console
python -m app.commands.seed_reference_data --source-mappings private/source_mappings.json
```

The command updates existing records by their stable keys and runs atomically.
Repeating it does not create duplicates. Omitting mappings leaves existing mappings
unchanged. Private mappings and the local database are ignored by Git; never add
production source URLs or the broadcast provider name to public files or fixtures.

## Schedule client and parsers

`app.scraper.client.ScheduleSourceClient` owns a reusable async HTTPX client.
Use it as an async context manager to close connections reliably. Load its
configuration with `load_schedule_source_config(Path("private/schedule_source.json"))`.
The ignored private file follows `private/schedule_source.example.json`; replace
the placeholder URL and CSS selectors privately before use.

Call `await client.daily_schedule(reference_date=page_date)` or
`await client.club_schedule(private_club_url, reference_date=page_date)`.
Both return tuples of validated `ScrapedMatch` records. Parsing can also be tested
without HTTP via `parse_daily_schedule` and `parse_club_schedule`.

The explicit reference date resolves yearless headers to the nearest valid date
in the previous, current or following year. Dates support ISO, day/month and
Portuguese month names. Structured kickoff metadata takes precedence over display
time. Otherwise local times are interpreted in `Europe/Lisbon` and converted to
UTC. Every kickoff hour is included. Ambiguous or nonexistent daylight-saving
times require offset-aware metadata; malformed matches fail the page rather than
silently returning partial results. Unknown layouts raise `ScheduleParseError`;
a recognized date-header table without match rows returns an empty tuple.

The client defaults to a 20-second HTTP timeout and two retries with exponential
delay for network/timeouts and HTTP 429/500/502/503/504 responses. Other HTTP errors
fail immediately. Nonempty HTML is required. Errors use generic messages without
embedding private URLs or response bodies. The implementation does not persist
matches, normalize names or schedule scraping jobs; those belong to later issues.

Tests use synthetic HTML and HTTPX mock transports, never production pages.
Local live verification on 9 November 2026 succeeded for all 37 configured pages:
630 unique matches saved, 109 within that seven-day agenda, zero source errors.
19 of those 109 had a channel still awaiting confirmation. These are observations,
not a guarantee of future source availability. TLS uses the operating system trust
store with certificate and hostname verification enabled.

## Name normalisation

`NameNormaliser(session, fallback=None)` resolves `club`, `competition` and
`channel` names asynchronously. Call `await normaliser.normalise(raw_name, context)`
to obtain a `NormalisedName` containing the display value, resolution method,
review flag and whether the result came from the cache.

Lookup keys fold case and accents, normalize whitespace and punctuation, and
preserve team suffixes, channel numbers and `+`. Manual cache entries take
precedence, followed by active canonical database names/slugs and club aliases.
Successful AI suggestions are reused from the existing `normalisation_cache`
table, scoped by context, with usage counters and timestamps. A newly added
deterministic match takes precedence over an older AI cache entry.

For optional Groq fallback, configure `JOGOCANAL_GROQ_API_KEY` and
`JOGOCANAL_GROQ_MODEL` privately. Construct
`GroqNormaliser(settings.groq_api_key, settings.groq_model)` only when both are
configured, use it as an async context manager, and pass it to `NameNormaliser`.
Choose a currently available model supporting JSON mode. The adapter follows
[Groq's chat completion API](https://console.groq.com/docs/api-reference), validates
the returned JSON locally and limits each request to 15 seconds and 128 output
tokens. Only the unknown name and its entity context are sent, never schedule
URLs or source configuration. There are no automatic retries of paid requests.

AI suggestions always require review and never create canonical entity records.
Disabled fallback, uncertainty, invalid responses and HTTP failures return the
original cleaned name as `unresolved`, requiring review, without caching a failed
lookup. This allows a later attempt to recover. The caller owns the database
transaction and must commit to persist cache writes and usage counts. The service
must not share an AsyncSession between concurrent tasks.
The database unique constraint prevents duplicate cache keys. Concurrent writers
must retry their transaction on a uniqueness conflict; the service does not commit
or roll back unrelated ingestion work.

Tests use synthetic names and mocked Groq responses; no live Groq call is made.

## Match persistence and scrape records

`await persist_run(session_factory, batches, trigger="scheduled")` persists
validated `SourceBatch` objects and returns a durable `ScrapeRun` ID. Each batch
contains `MatchInput` records with raw/display names, UTC kickoff, existing
competition/channel IDs, optional recognised club IDs, review metadata and an
optional source revision timestamp. The persistence boundary does not create
canonical entities from AI suggestions. Resolving catalogue IDs and fetching
pages are responsibilities of the ingestion caller.

The fingerprint hashes the generic provider key, UTC kickoff, competition ID and
ordered team identities (club IDs when known, otherwise normalized display names).
Daily and club pages from the same provider therefore deduplicate. Channels are
unioned across duplicate observations in one run; a subsequent run replaces the
previous channel set. Kickoff changes or newly resolved club identities produce a
new fingerprint; old records remain available and can become stale within a
confirmed coverage window. No fuzzy rescheduling guesses are made.

Each source batch and its successful counters/events commit atomically. A failed
batch rolls back its matches and channel links, then records a generic error in a
separate transaction. Other sources can succeed, yielding a `partial` run. Runs
record attempted/successful sources, parsed observations, inserts, updates,
caller-supplied unknown-term counts and errors. Source references are generic
identifiers, not operational URLs; raw exception text is never stored in events.

Stale marking requires `complete=True` and an explicit UTC half-open coverage
window (`window_start <= kickoff < window_end`). `club_id` optionally narrows that
scope. Failed, partial and unconfirmed empty results never mark records stale.
Empty confirmed coverage additionally requires `allow_empty=True`. Only unseen
future matches belonging to that provider/scope are marked, never deleted. A
match seen by any successful source in the run is protected. Reappearance clears
the stale flag. Older observations or older/missing revisions cannot overwrite
newer stored data.

The caller must serialize runs; execution locking belongs to the scraper CLI
issue. A database outage or process interruption can leave a run `running` for
later operational recovery. This issue adds no schema migration, production
database writes, network requests or scheduled jobs.

## Scraper CLI

Run `python -m app.commands.scrape --trigger manual` after configuring the private
source and importing reviewed competition/channel catalogue entries. The CLI
fetches the daily page and active tracked-club mappings, normalises names and
persists source batches under a shared OS process lock. See
[scraper operations and DirectAdmin cron](docs/operations/scraper-cron.md) for
catalogue setup, exit codes, timeouts, locking and the cron command template.
For an empty catalogue, add `--discover-catalogue` to the scraper or worker CLI
to retain literal competition/channel names and queue them for review. Without it,
the existing strict catalogue requirement remains. The production cron job has not
been installed.

## Web interface

The public interface uses FastAPI routes, Jinja templates and locally served
Bootstrap 5.3.8. Start it with `python -m uvicorn app.main:app --reload`, then visit
`http://127.0.0.1:8000/`. The shared shell includes responsive navigation,
Portuguese labels, an accessible skip link, active-page state and reusable heading
and empty-state macros. `/clubes` shows the seeded club directory.
The agenda reads persisted televised matches for today and the next six days.

Templates live in `app/templates`, web routes in `app/web/routes.py`, and custom
branding/styles in `app/static/brand` and `app/static/css`. Bootstrap files are
vendored under `app/static/vendor/bootstrap` with their MIT licence, so rendering
and navigation do not depend on a third-party CDN. No build step is required.

### Seven-day schedule

The agenda includes every kickoff from 00:00 through 23:59 in Europe/Lisbon,
including games earlier today. Local midnight boundaries are converted to UTC
before querying; daylight-saving weeks can contain 167 or 169 hours. Records are
ordered by UTC kickoff and ID, then grouped by Lisbon date. Empty dates remain
visible. Stale matches and records without channel relationships are excluded.

Public template data contains only match IDs, local kickoff timestamps, display
names, competitions and channels. Private source URLs, provider identifiers and
raw source names are not passed to templates. A database failure returns a safe
503 state rather than an empty schedule. Reading the agenda never triggers a
scrape or writes to the database. Search, counters and match status controls are implemented as described below.

### Responsive schedule (Issue #12)
The desktop table becomes mobile match cards. Local JavaScript filters teams, competitions and channels immediately, ignoring accents and case, and announces the visible count. All matches remain readable without JavaScript. Live, postponed and finished states require a recognised source status; upcoming within one hour is A SEGUIR. Past kickoffs without a source status remain POR CONFIRMAR; elapsed time alone never claims a match is live or finished.

### Club directory (Issue #13)
The directory reads confirmed memberships from the latest database season in divisions one and two. Active tracked clubs have dedicated /clubes/{slug} pages, using canonical IDs for their seven-day television schedule. Unknown or inactive clubs return 404. Crests are local assets.

### Public API (Issue #14)
GET /api/v1/matches returns seven Lisbon calendar days with start_date (default today), limit (1–100) and offset (0–10000). GET /api/v1/clubs returns the current directory grouped by division. GET /api/v1/clubs/{slug}/matches returns the same schedule contract for a tracked club. GET /api/v1/health checks database connectivity (503 when unavailable); /health remains the lightweight liveness endpoint. /docs describes the Pydantic schemas. Responses contain public display fields only.

### Private administration (Issue #15)

After `python -m alembic upgrade head`, create your administrator locally:

```powershell
python -m app.commands.create_admin your-email@example.com
```

Enter a unique 16–128-character passphrase at the hidden prompts, then open
`http://127.0.0.1:8000/admin/login`. There is no default account or public registration.
Passwords use salted scrypt (N=32768, r=8, p=3). Sessions expire after eight hours;
only token hashes are stored in the database. Logout revokes the current session;
disabling an account or changing its password hash invalidates existing sessions.
Login and mutating forms require CSRF tokens. SQLite-backed limits allow five
attempts per account and twenty per client IP per fifteen minutes. Run behind a
trusted proxy with correctly configured client-IP forwarding in production.
`JOGOCANAL_ENVIRONMENT=production` enables Secure, host-prefixed cookies; production
requires HTTPS. Admin responses are not cached. Expired sessions and throttle
records are removed during login. No administrator credentials are committed.

### Scraper dashboard and durable manual jobs (Issue #16)

Open `/admin/scraper` after logging in to inspect the latest 20 runs and jobs,
30 warnings/failures and 50 pending normalisation reviews. A manual request creates
one durable database job. Repeated or concurrent requests reuse the active job.
The HTTP request never runs the scraper, and closing the browser does not lose it.

Run one queued job from the project root:

```powershell
python -m app.commands.work_scrape_jobs
```

Schedule this command every minute on the same host as the scheduled scraper.
Both commands must use the same absolute `--lock-file` path and database. Exit 75
means the lock is busy; the pending job remains queued for the next worker run.
The worker records the run ID, completion or safe failure message. After an abrupt
process death, the next worker marks the interrupted job/run failed and releases
the slot; it does not automatically replay an uncertain update. An administrator
can then request a new job. The database enforces at most one pending/running job.

This is a single-host SQLite worker, not an in-process FastAPI background task.
The worker requires the existing private source configuration and reviewed
catalogue. Local live-source ingestion has been verified. Production worker/cron installation
remains a deployment step; no production job was installed.

The private selector profile optionally accepts status_selector. When configured, source match statuses flow through parsing, normalisation and persistence into public badges. An unconfigured or absent status stays unknown; no live state is invented. A duplicate club-page row without a status does not erase a status present on the same run's daily page. Live-source selector compatibility still requires private verification.

### Information pages (Issue #17)

`/quem-somos`, `/termos-e-condicoes` and `/politica-de-privacidade` share the global
footer with info@jogocanal.com and the developer credit. `/sobre` remains available.
The privacy text reflects the implemented application (no public analytics cookies,
local search, administrator sessions and throttling). Operator identity, hosting,
log retention and email-service arrangements must be confirmed for the actual
production environment before publishing there; these deployment details have not
been invented. Privacy-rights information links to the CNPD.

### Ad placement preview (Issue #18, first stage)

In local development, visit `/?ads_preview=1` to inspect labelled, inert ad
placeholders: a 90px-high desktop top banner (up to 970px wide), a 300x250
desktop-only sidebar slot, and one 300x250 slot after the
first nonempty day (when another day follows). Mobile uses a shorter top banner.
Search hides the inline slot so it cannot interrupt filtered results.
The club directory has a top banner and one 728x90 banner between divisions.
Individual clubs show one rectangle after their schedule, or a short banner after
an empty state. About/Who We Are show one rectangle after their content; legal
pages stay ad-free. Mobile banners are up to 320x100; rectangles remain up to
300x250, shrinking to fit narrower screens. Preview navigation preserves the flag.
These are initial layout choices, not a claim of optimal revenue.
The normal URL is unchanged; production disables this preview even with the query
parameter. No Google scripts, ad requests or consent cookies are introduced.
Consent management, real AdSense units and ads.txt remain pending for Issue #18.
