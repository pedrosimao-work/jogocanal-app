from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PublicMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kickoff: datetime
    home: str
    away: str
    home_club_id: int | None
    away_club_id: int | None
    competition: str
    channels: tuple[str, ...]
    status: str
    status_label: str


class MatchPage(BaseModel):
    start_date: date
    timezone: str = "Europe/Lisbon"
    total: int
    limit: int
    offset: int
    items: list[PublicMatchResponse]


class PublicClubResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    short_name: str
    crest_path: str | None


class DivisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    season: str
    clubs: list[PublicClubResponse]


class ServiceHealth(BaseModel):
    status: Literal["ok", "unavailable"]
    database: Literal["ok", "unavailable"]
