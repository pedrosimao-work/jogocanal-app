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
