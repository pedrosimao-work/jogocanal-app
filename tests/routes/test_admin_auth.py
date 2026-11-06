from datetime import UTC, datetime, timedelta

import pytest
from bs4 import BeautifulSoup
from sqlalchemy import select

from app.commands.create_admin import create_admin
from app.models.admin_session import AdminSession
from app.models.admin_user import AdminUser
from app.services.auth import password_hash, verify_password

PASSWORD = "test-only long passphrase 2026"


async def login(client, password=PASSWORD):
    page = await client.get("/admin/login")
    csrf = BeautifulSoup(page.text, "html.parser").select_one("[name=csrf]")["value"]
    return await client.post(
        "/admin/login", data={"email": "admin@example.invalid", "password": password, "csrf": csrf}
    )


async def test_admin_session_csrf_rotation_and_logout(client, web_session):
    await create_admin(web_session, "admin@example.invalid", PASSWORD)
    assert (await client.get("/admin")).status_code == 303
    assert (
        await client.post("/admin/login", data={"email": "a", "password": PASSWORD})
    ).status_code == 403
    response = await login(client)
    assert response.status_code == 303
    cookie = client.cookies.get("jc_session")
    assert (
        "HttpOnly" in response.headers["set-cookie"]
        and "SameSite=strict" in response.headers["set-cookie"]
    )
    assert response.headers["cache-control"] == "no-store"
    assert (await client.get("/admin")).status_code == 200
    await login(client)
    assert client.cookies.get("jc_session") != cookie
    assert len((await web_session.scalars(select(AdminSession))).all()) == 1
    home = await client.get("/admin")
    csrf = BeautifulSoup(home.text, "html.parser").select_one("[name=csrf]")["value"]
    assert (await client.post("/admin/logout", data={"csrf": "wrong"})).status_code == 403
    assert (await client.post("/admin/logout", data={"csrf": csrf})).status_code == 303
    assert (await client.get("/admin")).status_code == 303
    client.cookies.set("jc_session", cookie)
    assert (await client.get("/admin")).status_code == 303


async def test_auth_expiry_disable_and_password_change(client, web_session):
    await create_admin(web_session, "admin@example.invalid", PASSWORD)
    await login(client)
    session = await web_session.scalar(select(AdminSession))
    session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await web_session.commit()
    assert (await client.get("/admin")).status_code == 303
    await login(client)
    admin = await web_session.scalar(select(AdminUser))
    admin.is_active = False
    await web_session.commit()
    assert (await client.get("/admin")).status_code == 303
    admin.is_active = True
    admin.password_hash = password_hash("another long test passphrase")
    await web_session.commit()
    assert (await client.get("/admin")).status_code == 303


async def test_wrong_password_throttling_and_form_bounds(client, web_session):
    await create_admin(web_session, "admin@example.invalid", PASSWORD)
    for _ in range(5):
        assert (await login(client, "wrong-but-long-password")).status_code == 401
    assert (await login(client)).status_code == 429
    assert (
        await client.post(
            "/admin/login",
            content="x" * 5000,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
    ).status_code == 413
    assert (await client.post("/admin/login", json={})).status_code == 415
    assert (await client.get("/admin/register")).status_code == 404
    assert "/admin" not in (await client.get("/openapi.json")).text


def test_password_hash_has_salt_and_rejects_invalid():
    hashed = password_hash(PASSWORD)
    assert hashed != password_hash(PASSWORD)
    assert verify_password(PASSWORD, hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password(PASSWORD, "invalid")
    with pytest.raises(ValueError):
        password_hash("short")


async def test_creation_rejects_duplicates_and_invalid_email(web_session):
    await create_admin(web_session, "ADMIN@example.invalid", PASSWORD)
    with pytest.raises(ValueError):
        await create_admin(web_session, "admin@example.invalid", PASSWORD)
    with pytest.raises(ValueError):
        await create_admin(web_session, "not-email", PASSWORD)


async def test_production_cookie_flags_and_csrf_unicode(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "environment", "production")
    response = await client.get("/admin/login")
    assert "__Host-jc_login=" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    response = await client.post("/admin/login", data={"csrf": "é" * 64})
    assert response.status_code == 403
