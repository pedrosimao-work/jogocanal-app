# Scraper command and DirectAdmin cron

Status: command and scheduling instructions prepared. No production cron job has
been installed. Deployment requires separate approval and a successful manual run
from the production host, including verification of live source compatibility.

## Prepare the host

Use Python 3.11 and the application's virtual environment. Install
`requirements.txt`, configure private environment variables and run Alembic
migrations and reference-data seeding. Import verified private source mappings.
The command reads active mappings for tracked clubs from the database, not from
the example JSON file.

Create `private/catalogue.json` using `private/catalogue.example.json` as the
format reference. Supply operator-reviewed competition and channel names/slugs;
the example names are not production catalogue data. Import them explicitly:

```console
python -m app.commands.seed_catalogue private/catalogue.json
```

The import is transactional and idempotent by slug. It does not remove entries
omitted from the file. An unknown competition or channel causes that source batch
to fail safely; the scraper never creates catalogue entries from AI guesses.

Set up the ignored `private/schedule_source.json` with verified URLs and selectors.
If using Groq, set both private API key and model environment variables. Never put
secrets in the cron command. Run from the application directory so `.env` and
relative paths resolve correctly. Ensure the database and lock directory are
writable by the same account that owns the cron job.

## Manual check

```console
python -m app.commands.scrape --trigger manual
```

Options include `--config PATH`, `--lock-file PATH`, `--timeout SECONDS` (default
900), and `--delay SECONDS` (default 0.5 between source requests). The date reference
uses Europe/Lisbon regardless of the host timezone. HTTP retries remain bounded by
the source client. Scraping runs outside FastAPI and Passenger request processing.

The persistent lock file uses an OS lock released on normal exit or process death.
Do not delete or replace the lock file to clear contention. Every invocation on
the host must use the same absolute lock path, including administrator jobs. This
is a single-host lock, not a distributed lock across multiple servers.

| Exit code | Meaning |
| --- | --- |
| 0 | All attempted source batches completed |
| 1 | Failed run, timeout, configuration or database error |
| 2 | Invalid CLI arguments |
| 3 | Partial run: at least one source failed |
| 75 | Lock unavailable; overlapping execution skipped |
| 130 | Keyboard interruption |

Output contains a run ID and status or a generic safe error. Detailed source
values and credentials are not printed. Run records begin before fetching; normal
cancellation is recorded as failed. A hard kill or database outage can leave a
`running` record for operator review; the OS lock still releases on process exit.
The pipeline does not assert complete source coverage, so it preserves unseen
matches instead of inferring stale status from the observed date range.

## Install only after deployment approval

In DirectAdmin **User Level → Cron Jobs**, use the account's cron interface
([DirectAdmin documentation](https://docs.directadmin.com/directadmin/general-usage/)).
Suggested initial schedule: minute `*/30`, hour/day/month/weekday `*`. Confirm the
host's cron timezone and any source request-frequency restrictions before enabling.

Use this command template with real paths supplied privately:

```sh
cd /absolute/application/path && /absolute/venv/bin/python -m app.commands.scrape --trigger scheduled --lock-file /absolute/private/path/scraper.lock >> /absolute/private/logs/scraper.log 2>&1
```

Create the private log directory first and arrange log rotation. Do not put logs
under the public web root. Keep only one scheduled scraper entry, verify a run
record after the first scheduled execution, and monitor nonzero exit statuses.
To disable scheduling, remove or disable that cron entry; this does not terminate
an already running process. No cron entry is created by the Python command itself.
