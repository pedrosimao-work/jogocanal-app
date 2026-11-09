import pytest
from bs4 import BeautifulSoup
from httpx import AsyncClient


@pytest.mark.parametrize(
    "path,label", [("/", "Agenda"), ("/clubes", "Clubes"), ("/sobre", "Sobre")]
)
async def test_shared_layout_and_active_navigation(
    client: AsyncClient, path: str, label: str
) -> None:
    response = await client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    page = BeautifulSoup(response.text, "html.parser")
    assert page.html["lang"] == "pt-PT"
    assert len(page.select("h1")) == 1
    assert page.select_one('[aria-current="page"]').get_text(strip=True) == label
    assert page.select_one('a[href="#main-content"]')
    assert page.select_one('button[aria-controls="main-navigation"]')
    for element in page.select('link[rel="stylesheet"], script[src], img[src]'):
        url = element.get("href") or element.get("src")
        assert url.startswith("http://testserver/static/")
        assert (await client.get(url)).status_code == 200


async def test_static_mount_cannot_expose_private_files(client: AsyncClient) -> None:
    response = await client.get("/static/..%2F..%2Fprivate%2Fsource_mappings.json")
    assert response.status_code == 404


async def test_web_routes_do_not_pollute_public_api_schema(client: AsyncClient) -> None:
    paths = (await client.get("/openapi.json")).json()["paths"]
    assert "/health" in paths and "/clubes" not in paths and "/" not in paths


async def test_ad_preview_is_opt_in_and_disabled_in_production(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "environment", "development")
    assert 'class="ad-preview ' not in (await client.get("/")).text
    preview = BeautifulSoup((await client.get("/?ads_preview=1")).text, "html.parser")
    assert preview.select_one(".ad-preview--top")
    assert preview.select_one(".ad-preview--sidebar")
    assert not preview.select_one(".ad-preview--inline")  # No matches in this fixture.
    assert all("testserver/static/" in tag["src"] for tag in preview.select("script[src]"))
    monkeypatch.setattr(settings, "environment", "production")
    assert 'class="ad-preview ' not in (await client.get("/?ads_preview=1")).text


async def test_preview_navigation_and_content_pages(client, web_session, monkeypatch):
    from app.core.config import settings
    from app.models.club import Club
    from app.models.league import League, LeagueMembership

    monkeypatch.setattr(settings, "environment", "development")
    web_session.add_all(
        [
            Club(id=1, name="Example Club", short_name="Example", slug="example", is_tracked=True),
            League(id=1, name="Example League", slug="example", tier=1),
        ]
    )
    await web_session.flush()
    web_session.add(LeagueMembership(club_id=1, league_id=1, season="2026/2027", display_order=1))
    await web_session.flush()
    for path in ["/clubes", "/clubes/example", "/sobre", "/quem-somos"]:
        page = BeautifulSoup((await client.get(path + "?ads_preview=1")).text, "html.parser")
        assert page.select(".ad-preview"), path
        assert all("ads_preview=1" in a["href"] for a in page.select(".nav-link"))
        if path == "/clubes":
            assert "ads_preview=1" in page.select_one(".club-tile")["href"]
        assert 'class="ad-preview ' not in (await client.get(path)).text
    for path in ["/termos-e-condicoes", "/politica-de-privacidade"]:
        assert 'class="ad-preview ' not in (await client.get(path + "?ads_preview=1")).text
    monkeypatch.setattr(settings, "environment", "production")
    for path in ["/clubes", "/clubes/example", "/sobre"]:
        response = await client.get(path + "?ads_preview=1")
        assert 'class="ad-preview ' not in response.text
        assert "?ads_preview=1" not in response.text
