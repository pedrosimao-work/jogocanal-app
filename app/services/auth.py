"""Revocable database sessions and bounded, memory-hard password verification."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_session import AdminSession, LoginThrottle


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password: str, salt: str | None = None) -> str:
    if not 16 <= len(password) <= 128:
        raise ValueError("Use a password with 16 to 128 characters")
    salt = salt or secrets.token_hex(16)
    result = hashlib.scrypt(
        password.encode(),
        salt=bytes.fromhex(salt),
        n=32768,
        r=8,
        p=3,
        maxmem=64 * 1024 * 1024,
        dklen=32,
    )
    return f"scrypt$32768$8$3${salt}${result.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        parts = stored.split("$")
        if len(parts) != 6 or parts[:4] != ["scrypt", "32768", "8", "3"]:
            return False
        return secrets.compare_digest(password_hash(password, parts[4]), stored)
    except (ValueError, TypeError):
        return False


async def login_allowed(session: AsyncSession, email: str, address: str) -> bool:
    """SQLite atomic counters also work across ASGI workers; never log raw identifiers."""
    now = datetime.now(UTC)
    await session.execute(delete(LoginThrottle).where(LoginThrottle.expires_at <= now))
    await session.execute(delete(AdminSession).where(AdminSession.expires_at <= now))
    allowed = True
    for name, maximum in (("email:" + email, 5), ("ip:" + address, 20)):
        key = digest(name)
        statement = insert(LoginThrottle).values(
            key=key, attempts=1, expires_at=now + timedelta(minutes=15)
        )
        counter = statement.on_conflict_do_update(
            index_elements=[LoginThrottle.key], set_={"attempts": LoginThrottle.attempts + 1}
        ).returning(LoginThrottle.attempts)
        count = await session.scalar(counter)
        allowed = allowed and count is not None and count <= maximum
    await session.commit()
    return allowed
