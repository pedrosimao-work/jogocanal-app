"""Public, read-only seven-day schedule in Europe/Lisbon."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.match import Match, MatchChannel

LISBON = ZoneInfo("Europe/Lisbon")
WEEKDAYS = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)
MONTHS = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def lisbon_today() -> date:
    return datetime.now(LISBON).date()


def public_status(source: str | None, kickoff: datetime, now: datetime) -> tuple[str, str]:
    """Only authoritative source states imply live play or a completed match."""
    states = {
        "live": ("live", "AO VIVO"),
        "ao vivo": ("live", "AO VIVO"),
        "in_progress": ("live", "AO VIVO"),
        "postponed": ("postponed", "ADIADO"),
        "adiado": ("postponed", "ADIADO"),
        "finished": ("finished", "TERMINADO"),
        "completed": ("finished", "TERMINADO"),
        "terminado": ("finished", "TERMINADO"),
        "cancelled": ("postponed", "CANCELADO"),
    }
    if source and source.strip().casefold() in states:
        return states[source.strip().casefold()]
    seconds = (kickoff.astimezone(UTC) - now.astimezone(UTC)).total_seconds()
    if 0 <= seconds <= 3600:
        return "next", "A SEGUIR"
    return ("scheduled", "AGENDADO") if seconds > 0 else ("unknown", "POR CONFIRMAR")


def schedule_bounds(today: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(today, time.min, LISBON).astimezone(UTC),
        datetime.combine(today + timedelta(days=7), time.min, LISBON).astimezone(UTC),
    )


@dataclass(frozen=True)
class ScheduleMatch:
    id: int
    kickoff: datetime
    home: str
    away: str
    competition: str
    channels: tuple[str, ...]
    status: str = "scheduled"
    status_label: str = "AGENDADO"
    home_club_id: int | None = None
    away_club_id: int | None = None


@dataclass
class ScheduleDay:
    date: date
    label: str
    heading: str
    matches: list[ScheduleMatch] = field(default_factory=list)


async def seven_day_schedule(session: AsyncSession, today: date) -> list[ScheduleDay]:
    start, end = schedule_bounds(today)
    days = []
    for offset in range(7):
        day = today + timedelta(days=offset)
        label = (
            "Hoje"
            if offset == 0
            else "Amanhã"
            if offset == 1
            else WEEKDAYS[day.weekday()].capitalize()
        )
        days.append(ScheduleDay(day, label, f"{day.day} de {MONTHS[day.month - 1]}"))
    by_date = {day.date: day for day in days}
    records = await session.scalars(
        select(Match)
        .where(
            Match.kickoff_at >= start,
            Match.kickoff_at < end,
            Match.is_stale.is_(False),
            Match.channel_links.any(),
        )
        .options(
            selectinload(Match.competition),
            selectinload(Match.channel_links).selectinload(MatchChannel.channel),
        )
        .order_by(Match.kickoff_at, Match.id)
    )
    for record in records:
        kickoff = record.kickoff_at
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=UTC)
        kickoff = kickoff.astimezone(LISBON)
        by_date[kickoff.date()].matches.append(
            ScheduleMatch(
                record.id,
                kickoff,
                record.home_name_display,
                record.away_name_display,
                record.competition.name,
                tuple(
                    sorted({link.channel.name for link in record.channel_links}, key=str.casefold)
                ),
                *public_status(record.source_status, kickoff, datetime.now(UTC)),
                record.home_club_id,
                record.away_club_id,
            )
        )
    return days
