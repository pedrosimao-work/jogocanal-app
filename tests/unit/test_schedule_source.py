from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest

from app.scraper.client import ScheduleSourceClient
from app.scraper.config import load_schedule_source_config
from app.scraper.exceptions import (
    ScheduleParseError,
    ScheduleSourceError,
    ScheduleSourceRequestError,
)
from app.scraper.parsers import parse_club_schedule, parse_daily_schedule

CONFIG = load_schedule_source_config(
    Path(__file__).resolve().parents[2] / "private/schedule_source.example.json"
)
REFERENCE = date(2026, 11, 6)


def test_multiple_tables_preserve_all_matches_and_dates() -> None:
    matches = parse_daily_schedule(
        page("00:00") + page("23:59", "07/11/2026"),
        CONFIG.selectors,
        reference_date=REFERENCE,
    )
    assert [match.kickoff_at for match in matches] == [
        datetime(2026, 11, 6, tzinfo=UTC),
        datetime(2026, 11, 7, 23, 59, tzinfo=UTC),
    ]


def test_competition_does_not_leak_between_tables() -> None:
    second = page().replace('<tr class="competition-header"><th>Example League</th></tr>', "")
    with pytest.raises(ScheduleParseError):
        parse_daily_schedule(page() + second, CONFIG.selectors, reference_date=REFERENCE)


def test_invalid_selector_is_reported_as_parse_error() -> None:
    selectors = CONFIG.selectors.model_copy(update={"table_selector": "["})
    with pytest.raises(ScheduleParseError):
        parse_daily_schedule(page(), selectors, reference_date=REFERENCE)


def page(clock: str = "00:15", day: str = "6 de novembro de 2026", metadata: str = "") -> str:
    return f"""<table class="schedule club">
    <tr class="date-header"><th>{day}</th></tr>
    <tr class="competition-header"><th>Example League</th></tr>
    <tr><td class="time">{clock}{metadata}</td>
    <td class="home"><span>Home FC</span></td><td class="away"><span>Away FC</span></td>
    <td class="details"><label>Club Cup</label></td>
    <td class="channels"><ul class="channel-list"><li>Channel One</li>
    <li>Channel Two</li><li>Channel One</li></ul></td></tr></table>"""


@pytest.mark.parametrize("clock", ["00:00", "05:30", "12:00", "23:59"])
@pytest.mark.parametrize("parser", [parse_daily_schedule, parse_club_schedule])
def test_all_kickoff_times(parser, clock: str) -> None:
    (match,) = parser(page(clock), CONFIG.selectors, reference_date=REFERENCE)
    assert match.kickoff_at == datetime.fromisoformat(f"2026-11-06T{clock}:00+00:00")
    assert match.channels_raw == ("Channel One", "Channel Two")
    assert match.competition_raw == (
        "Example League" if parser is parse_daily_schedule else "Club Cup"
    )


@pytest.mark.parametrize(
    "day,expected",
    [
        ("2026-07-01", "2026-06-30T23:15:00+00:00"),
        ("01/01", "2027-01-01T00:15:00+00:00"),
        ("1 de março de 2026", "2026-03-01T00:15:00+00:00"),
    ],
)
def test_calendar_and_timezone(day: str, expected: str) -> None:
    (match,) = parse_daily_schedule(page(day=day), CONFIG.selectors, reference_date=REFERENCE)
    assert match.kickoff_at == datetime.fromisoformat(expected)


def test_structured_timestamp_overrides_display_time() -> None:
    (match,) = parse_club_schedule(
        page("TBD", metadata='<meta itemprop="startDate" content="2026-07-01T12:00:00+01:00">'),
        CONFIG.selectors,
        reference_date=REFERENCE,
    )
    assert match.kickoff_at == datetime(2026, 7, 1, 11, tzinfo=UTC)


@pytest.mark.parametrize(
    "html",
    [
        "<html>Blocked</html>",
        "<table class='schedule'></table>",
        page("25:00"),
        page("TBD"),
        page(day="unknown"),
        page(day="31/02/2026"),
        page("01:30", "2026-03-29"),
        page("01:30", "2026-10-25"),
        page().replace("<span>Home FC</span>", ""),
        page().replace("channel-list", "missing"),
    ],
)
def test_malformed_schedules_fail_explicitly(html: str) -> None:
    with pytest.raises(ScheduleParseError, match="could not be parsed safely"):
        parse_daily_schedule(html, CONFIG.selectors, reference_date=REFERENCE)


def test_recognized_empty_schedule() -> None:
    assert (
        parse_daily_schedule(
            '<table class="schedule"><tr class="date-header"><th>2026-11-06</th></tr></table>',
            CONFIG.selectors,
            reference_date=REFERENCE,
        )
        == ()
    )


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
async def test_http_retry_then_parse(status: int) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            status if calls == 1 else 200, text=page(), headers={"content-type": "text/html"}
        )

    async with ScheduleSourceClient(
        CONFIG, transport=httpx.MockTransport(handler), retry_delay=0
    ) as client:
        assert len(await client.daily_schedule(reference_date=REFERENCE)) == 1
        assert (
            len(
                await client.club_schedule("https://example.invalid/club", reference_date=REFERENCE)
            )
            == 1
        )
    assert calls == 3


@pytest.mark.parametrize("status,expected", [(404, 1), (403, 1), (503, 3)])
async def test_http_failure_is_bounded_and_private(status: int, expected: int) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status)

    async with ScheduleSourceClient(
        CONFIG, transport=httpx.MockTransport(handler), retry_delay=0
    ) as client:
        with pytest.raises(ScheduleSourceRequestError) as error:
            await client.fetch_html("https://example.invalid/private")
        assert str(error.value) == "Schedule request failed"
        assert calls == expected


async def test_timeout_retry_exhaustion() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("private URL", request=request)

    async with ScheduleSourceClient(
        CONFIG, transport=httpx.MockTransport(handler), retry_delay=0
    ) as client:
        with pytest.raises(ScheduleSourceRequestError, match="^Schedule request failed$"):
            await client.fetch_html("https://example.invalid")


@pytest.mark.parametrize("content_type,body", [("application/json", "{}"), ("text/html", " ")])
async def test_invalid_response(content_type: str, body: str) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=body, headers={"content-type": content_type})
    )
    async with ScheduleSourceClient(CONFIG, transport=transport) as client:
        with pytest.raises(ScheduleSourceRequestError):
            await client.fetch_html("https://example.invalid")


def test_config_errors_do_not_expose_private_input(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"homepage_url": "private"}', encoding="utf-8")
    with pytest.raises(ScheduleSourceError, match="^Invalid schedule-source configuration$"):
        load_schedule_source_config(path)


@pytest.mark.parametrize("status", ["AO VIVO", "ADIADO", "TERMINADO"])
def test_optional_source_status_is_parsed(status):
    selectors = CONFIG.selectors.model_copy(update={"status_selector": ".match-state"})
    html = page().replace("</tr></table>", f'<td class="match-state">{status}</td></tr></table>')
    assert (
        parse_daily_schedule(html, selectors, reference_date=REFERENCE)[0].source_status == status
    )
    assert (
        parse_daily_schedule(page(), selectors, reference_date=REFERENCE)[0].source_status is None
    )
