"""Parse schedule HTML without knowing the operational provider or its URLs."""

import re
import unicodedata
from datetime import UTC, date, datetime, time
from typing import Literal
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, Tag
from pydantic import ValidationError
from soupsieve.util import SelectorSyntaxError

from app.scraper.exceptions import ScheduleParseError
from app.scraper.schemas import ScheduleSourceSelectors, ScrapedMatch

MONTHS = (
    "janeiro",
    "fevereiro",
    "marco",
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


def _text(tag: Tag | None) -> str:
    return " ".join(tag.stripped_strings) if tag else ""


def _date(value: str, reference: date) -> date:
    normalized = "".join(
        c for c in unicodedata.normalize("NFD", value.lower()) if not unicodedata.combining(c)
    )
    iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", normalized)
    if iso:
        return date(*map(int, iso.groups()))
    numeric = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?\b", normalized)
    named = re.search(
        r"\b(\d{1,2})\s+(?:de\s+)?(" + "|".join(MONTHS) + r")(?:\s+(?:de\s+)?(\d{4}))?\b",
        normalized,
    )
    match = numeric or named
    if not match:
        raise ValueError("Unrecognized schedule date")
    day, month, year = match.groups()
    month_number = int(month) if numeric else MONTHS.index(month) + 1
    if year:
        return date(int(year), month_number, int(day))
    # Use an explicit page reference to resolve dates crossing New Year deterministically.
    candidates = []
    for candidate_year in (reference.year - 1, reference.year, reference.year + 1):
        try:
            candidates.append(date(candidate_year, month_number, int(day)))
        except ValueError:
            continue
    if not candidates:
        raise ValueError("Invalid schedule date")
    return min(candidates, key=lambda candidate: abs((candidate - reference).days))


def _localize(value: datetime, zone: ZoneInfo) -> datetime:
    if value.tzinfo is not None and value.utcoffset() is not None:
        return value.astimezone(UTC)
    candidates = {
        value.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        for fold in (0, 1)
        if value.replace(tzinfo=zone, fold=fold)
        .astimezone(UTC)
        .astimezone(zone)
        .replace(tzinfo=None)
        == value
    }
    if len(candidates) != 1:
        raise ValueError("Ambiguous or nonexistent local kickoff")
    return candidates.pop()


def _parse(
    html: str,
    selectors: ScheduleSourceSelectors,
    kind: Literal["daily_schedule", "club_schedule"],
    reference_date: date,
    timezone: str,
    source_reference: str | None,
) -> tuple[ScrapedMatch, ...]:
    try:
        zone = ZoneInfo(timezone)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.select(
            selectors.table_selector if kind == "daily_schedule" else selectors.club_table_selector
        )
        if not tables:
            raise ValueError("Schedule table missing")
        matches = []
        for table in tables:
            current_date = None
            competition = ""
            recognized = False
            for row in table.select("tr"):
                if row.find_parent("table") is not table:
                    continue
                classes = row.get_attribute_list("class")
                if selectors.date_header_class in classes or row.find(
                    class_=selectors.date_header_class
                ):
                    current_date = _date(_text(row), reference_date)
                    competition = ""
                    recognized = True
                    continue
                if selectors.competition_header_class in classes or row.find(
                    class_=selectors.competition_header_class
                ):
                    competition = _text(row)
                    recognized = True
                    continue
                home = row.select_one(selectors.home_selector)
                away = row.select_one(selectors.away_selector)
                clock = row.select_one(selectors.time_selector)
                if not any((home, away, clock)):
                    continue
                recognized = True
                metadata = row.select_one(selectors.start_date_selector)
                stamp = metadata.get("content") if metadata else None
                if isinstance(stamp, str) and stamp.strip():
                    kickoff = datetime.fromisoformat(stamp.strip().replace("Z", "+00:00"))
                else:
                    if current_date is None or not re.fullmatch(r"\d{1,2}:\d{2}", _text(clock)):
                        raise ValueError("Missing kickoff date or time")
                    hour, minute = map(int, _text(clock).split(":"))
                    kickoff = datetime.combine(current_date, time(hour, minute))
                container = row.select_one(selectors.channels_container_selector)
                channels = (
                    tuple(
                        dict.fromkeys(
                            _text(item)
                            for item in container.select(selectors.channel_item_selector)
                            if _text(item)
                        )
                    )
                    if container
                    else ()
                )
                row_competition = (
                    _text(row.select_one(selectors.club_competition_selector))
                    if kind == "club_schedule"
                    else competition
                )
                matches.append(
                    ScrapedMatch(
                        kickoff_at=_localize(kickoff, zone),
                        home_name_raw=_text(home),
                        away_name_raw=_text(away),
                        competition_raw=row_competition,
                        channels_raw=channels,
                        source_kind=kind,
                        source_reference=source_reference,
                    )
                )
            if not recognized:
                raise ValueError("Unrecognized schedule table")
        return tuple(matches)
    except (ValueError, ValidationError, SelectorSyntaxError, KeyError):
        # Never include HTML, private URLs, or validation input in public diagnostics.
        raise ScheduleParseError("Schedule HTML could not be parsed safely") from None


def parse_daily_schedule(
    html: str,
    selectors: ScheduleSourceSelectors,
    *,
    reference_date: date,
    timezone: str = "Europe/Lisbon",
    source_reference: str | None = None,
) -> tuple[ScrapedMatch, ...]:
    return _parse(html, selectors, "daily_schedule", reference_date, timezone, source_reference)


def parse_club_schedule(
    html: str,
    selectors: ScheduleSourceSelectors,
    *,
    reference_date: date,
    timezone: str = "Europe/Lisbon",
    source_reference: str | None = None,
) -> tuple[ScrapedMatch, ...]:
    return _parse(html, selectors, "club_schedule", reference_date, timezone, source_reference)
