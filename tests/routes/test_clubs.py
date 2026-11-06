from datetime import UTC, datetime

from app.models.club import Club
from app.models.league import League, LeagueMembership
from app.models.match import Match
from app.services.clubs import club_directory
from tests.routes.test_schedule_page import seed_catalogue, seed_match


async def test_directory_filters_and_club_schedule(client, web_session):
    clubs = [
        Club(id=i, name=f"Club {i}", short_name=f"C{i}", slug=f"club-{i}", is_tracked=True)
        for i in (1, 2)
    ]
    web_session.add_all(clubs + [League(id=1, name="First", slug="first", tier=1)])
    await web_session.flush()
    web_session.add_all(
        [
            LeagueMembership(club_id=1, league_id=1, season="2026/2027", display_order=1),
            LeagueMembership(club_id=2, league_id=1, season="2025/2026", display_order=1),
        ]
    )
    await web_session.flush()
    groups = await club_directory(web_session)
    assert [club.id for club in groups[0].clubs] == [1]
    response = await client.get("/clubes")
    assert "/clubes/club-1" in response.text and "/clubes/club-2" not in response.text
    await seed_catalogue(web_session)
    await seed_match(web_session, datetime.now(UTC), 1)
    record = await web_session.get(Match, 1)
    record.home_club_id = 1
    await web_session.flush()
    response = await client.get("/clubes/club-1")
    assert response.status_code == 200 and "Channel One" in response.text
    assert "private-provider-sentinel" not in response.text
    assert "Channel One" not in (await client.get("/clubes/club-2")).text
    assert (await client.get("/clubes/missing")).status_code == 404
    clubs[0].is_active = False
    await web_session.flush()
    assert (await client.get("/clubes/club-1")).status_code == 404
