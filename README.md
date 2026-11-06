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
