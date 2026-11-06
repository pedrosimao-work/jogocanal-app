from datetime import UTC, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MatchInput(BaseModel):
    """Persistence boundary: IDs must refer to existing canonical catalogue records."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)
    kickoff_at: datetime
    home_name_raw: str = Field(min_length=1, max_length=160)
    away_name_raw: str = Field(min_length=1, max_length=160)
    home_name_display: str = Field(min_length=1, max_length=160)
    away_name_display: str = Field(min_length=1, max_length=160)
    competition_id: int = Field(gt=0)
    home_club_id: int | None = Field(default=None, gt=0)
    away_club_id: int | None = Field(default=None, gt=0)
    channel_ids: frozenset[int] = Field(min_length=1)
    needs_review: bool = False
    unknown_terms: int = Field(default=0, ge=0)
    source_updated_at: datetime | None = None
    source_status: str | None = Field(default=None, max_length=40)

    @field_validator("kickoff_at", "source_updated_at")
    @classmethod
    def utc_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.utcoffset() is None:
            raise ValueError("Timezone-aware timestamps required")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def valid_sides_and_channels(self) -> Self:
        if self.home_club_id is not None and self.home_club_id == self.away_club_id:
            raise ValueError("Home and away clubs must differ")
        if any(value <= 0 for value in self.channel_ids):
            raise ValueError("Channel IDs must be positive")
        return self


class SourceBatch(BaseModel):
    """One complete or partial source result and its explicitly declared coverage."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    reference: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    provider_key: str = Field(default="primary_schedule", pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    matches: tuple[MatchInput, ...] = ()
    successful: bool = True
    complete: bool = False
    allow_empty: bool = False
    window_start: datetime | None = None
    window_end: datetime | None = None
    club_id: int | None = Field(default=None, gt=0)

    @field_validator("window_start", "window_end")
    @classmethod
    def utc_window(cls, value: datetime | None) -> datetime | None:
        return MatchInput.utc_timestamp(value)

    @model_validator(mode="after")
    def validate_coverage(self) -> Self:
        if not self.successful and self.matches:
            raise ValueError("Failed sources cannot supply matches")
        if self.complete:
            if (
                self.window_start is None
                or self.window_end is None
                or self.window_start >= self.window_end
            ):
                raise ValueError("Complete sources require an ordered coverage window")
            for match in self.matches:
                if not self.window_start <= match.kickoff_at < self.window_end:
                    raise ValueError("Match outside declared coverage window")
                if self.club_id is not None and self.club_id not in (
                    match.home_club_id,
                    match.away_club_id,
                ):
                    raise ValueError("Match outside declared club scope")
        return self
