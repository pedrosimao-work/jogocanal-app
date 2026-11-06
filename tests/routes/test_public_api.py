from datetime import UTC, datetime

from sqlalchemy.exc import OperationalError

from app.models.club import Club
from app.models.match import Match
from tests.routes.test_schedule_page import seed_catalogue, seed_match


async def test_api_matches_pagination_and_private_field_exclusion(client, web_session):
    await seed_catalogue(web_session)
    for number in range(3):
        await seed_match(web_session, datetime(2026, 11, 6, 15, number, tzinfo=UTC), number)
    response = await client.get("/api/v1/matches?start_date=2026-11-06&limit=1&offset=1")
    data = response.json()
    assert response.status_code == 200 and data["total"] == 3
    assert data["items"][0]["home"] == "Home 1"
    assert len(data["items"]) == 1
    assert data["items"][0]["kickoff"].endswith("Z") or data["items"][0]["kickoff"].endswith(
        "+00:00"
    )
    assert "private" not in response.text and "raw-home" not in response.text
    for query in ("limit=101", "offset=-1", "start_date=bad", "start_date=9999-12-31"):
        assert (await client.get("/api/v1/matches?" + query)).status_code == 422
    assert (await client.get("/api/v1/clubs")).json() == []
    assert (await client.get("/api/v1/clubs/missing/matches")).status_code == 404
    club = Club(name="Example", short_name="Example", slug="example", is_tracked=True)
    web_session.add(club)
    await web_session.flush()
    match = await web_session.get(Match, 1)
    match.away_club_id = club.id
    await web_session.flush()
    response = await client.get("/api/v1/clubs/example/matches?start_date=2026-11-06")
    assert response.json()["total"] == 1


async def test_api_readiness_checks_database(client, web_session, monkeypatch):
    response = await client.get("/api/v1/health")
    assert response.json() == {"status": "ok", "database": "ok"}
    assert response.headers["cache-control"] == "no-store"

    async def fail(*args, **kwargs):
        raise OperationalError("private connection string", {}, Exception())

    monkeypatch.setattr(web_session, "execute", fail)
    response = await client.get("/api/v1/health")
    assert response.status_code == 503 and "private" not in response.text
