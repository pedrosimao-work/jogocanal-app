import asyncio
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, cast
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse, RedirectResponse, Response

from app.core.config import settings
from app.db.dependencies import get_db_session
from app.models.admin_session import AdminSession
from app.models.admin_user import AdminUser
from app.services.auth import digest, login_allowed, password_hash, verify_password
from app.web.routes import templates

router = APIRouter(prefix="/admin", include_in_schema=False)
Session = Annotated[AsyncSession, Depends(get_db_session)]
SESSION_SECONDS = 8 * 3600
HASH_SLOTS = asyncio.Semaphore(2)
# Same work for an unknown account; never expose whether an email exists.
DUMMY_HASH = password_hash("unusable dummy password " + secrets.token_hex(16))


def cookie_name(kind: str) -> str:
    return ("__Host-" if settings.environment == "production" else "") + "jc_" + kind


def set_cookie(response: Response, kind: str, value: str, age: int) -> None:
    response.set_cookie(
        cookie_name(kind),
        value,
        max_age=age,
        httponly=True,
        secure=settings.environment == "production",
        samesite="strict",
        path="/",
    )


async def read_form(request: Request) -> dict[str, str]:
    if request.headers.get("content-type", "").split(";")[0] != "application/x-www-form-urlencoded":
        raise HTTPException(415, "Unsupported form")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 4096:
            raise HTTPException(413, "Form too large")
    try:
        values = parse_qs(body.decode(), max_num_fields=10)
    except (ValueError, UnicodeError) as error:
        raise HTTPException(400, "Invalid form") from error
    if any(len(value) != 1 for value in values.values()):
        raise HTTPException(400, "Duplicate field")
    return {key: value[0] for key, value in values.items()}


def check_csrf(request: Request, form: dict[str, str], kind: str = "session") -> None:
    token = request.cookies.get(cookie_name(kind), "")
    supplied = form.get("csrf", "")
    if (
        len(token) != 64
        or len(supplied) != 64
        or not all(c in "0123456789abcdef" for c in supplied)
        or not secrets.compare_digest(digest("csrf:" + token), supplied)
    ):
        raise HTTPException(403, "Invalid form token")


async def require_admin(request: Request, session: Session) -> AdminUser:
    token = request.cookies.get(cookie_name("session"), "")
    if len(token) == 64:
        row = (
            await session.execute(
                select(AdminSession, AdminUser)
                .join(AdminUser, AdminUser.id == AdminSession.admin_id)
                .where(
                    AdminSession.token_hash == digest(token),
                    AdminSession.expires_at > datetime.now(UTC),
                    AdminUser.is_active.is_(True),
                )
            )
        ).first()
        if row and secrets.compare_digest(row[0].password_version, digest(row[1].password_hash)):
            return cast(AdminUser, row[1])
    raise HTTPException(303, headers={"Location": str(request.url_for("admin_login"))})


Admin = Annotated[AdminUser, Depends(require_admin)]


def login_response(request: Request, error: str | None = None, status: int = 200) -> HTMLResponse:
    token = secrets.token_hex(32)
    response = templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={
            "title": "Administração",
            "page": "admin",
            "year": datetime.now(UTC).year,
            "csrf": digest("csrf:" + token),
            "error": error,
        },
    )
    response.status_code = status
    set_cookie(response, "login", token, 1800)
    return response


@router.get("/login", response_class=HTMLResponse, name="admin_login")
async def login_page(request: Request) -> HTMLResponse:
    return login_response(request)


@router.post("/login", name="admin_login_submit")
async def login(request: Request, session: Session) -> Response:
    form = await read_form(request)
    check_csrf(request, form, "login")
    email = form.get("email", "").strip().casefold()[:254]
    password = form.get("password", "")
    address = request.client.host if request.client else "unknown"
    if not await login_allowed(session, email, address):
        raise HTTPException(
            429, "Tenta novamente dentro de 15 minutos", headers={"Retry-After": "900"}
        )
    admin = await session.scalar(select(AdminUser).where(AdminUser.email == email))
    async with HASH_SLOTS:
        valid = await asyncio.to_thread(
            verify_password, password, admin.password_hash if admin else DUMMY_HASH
        )
    if not valid or admin is None or not admin.is_active:
        raise HTTPException(401, "Credenciais inválidas")
    token = secrets.token_hex(32)
    # Reauthentication rotates and revokes this browser's old session.
    old = request.cookies.get(cookie_name("session"), "")
    await session.execute(delete(AdminSession).where(AdminSession.token_hash == digest(old)))
    session.add(
        AdminSession(
            token_hash=digest(token),
            admin_id=admin.id,
            password_version=digest(admin.password_hash),
            expires_at=datetime.now(UTC) + timedelta(seconds=SESSION_SECONDS),
        )
    )
    admin.last_login_at = datetime.now(UTC)
    await session.commit()
    response = RedirectResponse(request.url_for("admin_home"), status_code=303)
    set_cookie(response, "session", token, SESSION_SECONDS)
    response.delete_cookie(cookie_name("login"), path="/")
    return response


@router.get("", name="admin_home", response_class=HTMLResponse)
async def home(request: Request, admin: Admin) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="admin/home.html",
        context={
            "title": "Administração",
            "page": "admin",
            "year": datetime.now(UTC).year,
            "admin": admin,
            "csrf": digest("csrf:" + request.cookies[cookie_name("session")]),
        },
    )


@router.post("/logout", name="admin_logout")
async def logout(request: Request, session: Session, admin: Admin) -> Response:
    form = await read_form(request)
    check_csrf(request, form)
    await session.execute(
        delete(AdminSession).where(
            AdminSession.token_hash == digest(request.cookies[cookie_name("session")])
        )
    )
    await session.commit()
    response = RedirectResponse(request.url_for("admin_login"), status_code=303)
    response.delete_cookie(cookie_name("session"), path="/")
    return response
