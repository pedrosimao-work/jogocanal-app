"""Create an administrator interactively; passwords never enter command arguments."""

import argparse
import asyncio
import getpass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminUser
from app.services.auth import password_hash


async def create_admin(session: AsyncSession, email: str, password: str) -> None:
    email = email.strip().casefold()
    if len(email) > 254 or email.count("@") != 1 or any(char.isspace() for char in email):
        raise ValueError("Enter a valid email")
    if await session.scalar(select(AdminUser.id).where(AdminUser.email == email)):
        raise ValueError("Administrator already exists")
    hashed = await asyncio.to_thread(password_hash, password)
    session.add(AdminUser(email=email, password_hash=hashed, is_active=True))
    await session.commit()


async def execute(email: str, password: str) -> None:
    from app.db.session import async_session_factory, engine

    try:
        async with async_session_factory() as session:
            await create_admin(session, email, password)
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a private administrator")
    parser.add_argument("email")
    args = parser.parse_args()
    password = getpass.getpass("Password (16–128 characters): ")
    if password != getpass.getpass("Confirm password: "):
        print("Passwords do not match")
        return 1
    try:
        asyncio.run(execute(args.email, password))
    except Exception:
        print(
            "Could not create administrator. Check email, password length, existing account and migrations."
        )
        return 1
    print("Administrator created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
