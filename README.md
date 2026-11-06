# jogocanal-app
FastAPI application for discovering where and when football matches are broadcast in Portugal.

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
Live compatibility must be checked in an environment that can reach the private
source; the implementation environment could not connect to either sampled page.
