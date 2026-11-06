import pytest
from bs4 import BeautifulSoup


@pytest.mark.parametrize(
    "path,title",
    [
        ("/quem-somos", "Quem Somos"),
        ("/termos-e-condicoes", "Termos e Condições"),
        ("/politica-de-privacidade", "Política de Privacidade"),
    ],
)
async def test_information_pages_and_global_footer(client, path, title):
    response = await client.get(path)
    page = BeautifulSoup(response.text, "html.parser")
    assert response.status_code == 200 and page.h1.get_text(strip=True) == title
    assert len(page.select("h1")) == 1
    footer = page.footer
    assert "Desenvolvido por" in footer.get_text()
    assert footer.select_one('a[href="https://pedrosimao.work"]')
    assert footer.select_one('a[href="mailto:info@jogocanal.com"]')
    for link in footer.select("nav a"):
        assert (await client.get(link["href"])).status_code == 200
    assert "set-cookie" not in response.headers


async def test_footer_is_present_on_agenda_and_club_directory(client):
    for path in ("/", "/clubes", "/sobre"):
        page = BeautifulSoup((await client.get(path)).text, "html.parser")
        assert len(page.footer.select("nav a")) == 3
        assert page.footer.select_one('a[href="mailto:info@jogocanal.com"]')
