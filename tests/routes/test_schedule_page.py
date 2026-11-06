from datetime import UTC, date, datetime, timedelta

import pytest
from bs4 import BeautifulSoup
from httpx import AsyncClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.channel import Channel
from app.models.competition import Competition
from app.models.match import Match, MatchChannel
from app.services.schedule import LISBON, lisbon_today, schedule_bounds, seven_day_schedule


async def seed_match(
    session: AsyncSession,
    stamp: datetime,
    number: int,
    *,
    stale: bool = False,
    televised: bool = True,
) -> None:
    record = Match(
        fingerprint=f"{number:064d}",
        kickoff_at=stamp,
        home_name_raw="raw-home",
        away_name_raw="raw-away",
        home_name_display=f"Home {number}",
        away_name_display="Away",
        competition_id=1,
        provider_key="private-provider-sentinel",
        source_url="https://example.invalid/private-source",
        is_stale=stale,
    )
    session.add(record)
    await session.flush()
    if televised:
        session.add(MatchChannel(match_id=record.id, channel_id=1))
    await session.flush()


async def seed_catalogue(session: AsyncSession) -> None:
    session.add_all(
        [
            Competition(id=1, name="Example Cup", slug="example-cup"),
            Channel(id=1, name="Channel One", slug="channel-one"),
        ]
    )
    await session.flush()


@pytest.mark.parametrize("today", [date(2026, 7, 1), date(2026, 12, 29)])
async def test_all_day_boundaries_and_seven_day_window(
    web_session: AsyncSession, today: date
) -> None:
    await seed_catalogue(web_session)
    start, end = schedule_bounds(today)
    stamps = [
        start - timedelta(microseconds=1),
        start,
        start + timedelta(hours=4),
        end - timedelta(minutes=1),
        end,
    ]
    for number, stamp in enumerate(stamps):
        await seed_match(web_session, stamp, number)
    await seed_match(web_session, start + timedelta(hours=6), 10, stale=True)
    await seed_match(web_session, start + timedelta(hours=7), 11, televised=False)
    days = await seven_day_schedule(web_session, today)
    assert len(days) == 7 and days[-1].date == today + timedelta(days=6)
    matches = [match for day in days for match in day.matches]
    assert [match.home for match in matches] == ["Home 1", "Home 2", "Home 3"]
    assert matches[0].kickoff.strftime("%H:%M") == "00:00"
    assert matches[-1].kickoff.strftime("%H:%M") == "23:59"
    assert all(match.channels == ("Channel One",) for match in matches)


@pytest.mark.parametrize("today,hours", [(date(2026, 3, 29), 167), (date(2026, 10, 25), 169)])
def test_dst_window_uses_local_midnights(today: date, hours: int) -> None:
    start, end = schedule_bounds(today)
    assert (end - start).total_seconds() / 3600 == hours


async def test_fall_back_repeated_hour_remains_chronological(web_session: AsyncSession) -> None:
    await seed_catalogue(web_session)
    await seed_match(web_session, datetime(2026, 10, 25, 1, 30, tzinfo=UTC), 2)
    await seed_match(web_session, datetime(2026, 10, 25, 0, 30, tzinfo=UTC), 1)
    day = (await seven_day_schedule(web_session, date(2026, 10, 25)))[0]
    assert [item.home for item in day.matches] == ["Home 1", "Home 2"]
    assert [item.kickoff.strftime("%H:%M") for item in day.matches] == ["01:30", "01:30"]
    assert day.matches[0].kickoff.utcoffset() != day.matches[1].kickoff.utcoffset()


async def test_public_schedule_escapes_text_and_excludes_operational_fields(
    client: AsyncClient, web_session: AsyncSession
) -> None:
    today = date(2026, 11, 6)
    app.dependency_overrides[lisbon_today] = lambda: today
    try:
        await seed_catalogue(web_session)
        await seed_match(web_session, datetime(2026, 11, 6, tzinfo=LISBON), 1)
        record = await web_session.get(Match, 1)
        record.home_name_display = '<script>alert("x")</script>'
        await web_session.flush()
        response = await client.get("/")
        assert response.status_code == 200
        assert (
            "private-provider-sentinel" not in response.text
            and "private-source" not in response.text
        )
        assert "raw-home" not in response.text
        assert "&lt;script&gt;" in response.text
        page = BeautifulSoup(response.text, "html.parser")
        assert len(page.select(".schedule-day")) == 7
        assert len(page.select(".schedule-days a")) == 7
        assert page.select_one("time").get_text() == "00:00"
    finally:
        app.dependency_overrides.pop(lisbon_today, None)


async def test_database_failure_is_not_reported_as_no_games(
    client: AsyncClient, monkeypatch
) -> None:
    async def failed(*args):
        raise OperationalError("private database details", {}, Exception())

    monkeypatch.setattr("app.web.routes.seven_day_schedule", failed)
    response = await client.get("/")
    assert response.status_code == 503
    assert "temporariamente indisponível" in response.text
    assert "private database details" not in response.text
