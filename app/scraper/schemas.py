from datetime import (  # Import timezone-aware datetime tools for canonical UTC kickoff timestamps
    UTC,
    datetime,
)
from typing import Literal  # Import Literal so parsed page types are restricted to known values

from pydantic import (  # Import validation tools for source configuration and parsed matches
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class ScheduleSourceSelectors(
    BaseModel
):  # Define the private CSS-selector profile required by the generic HTML parser
    model_config = ConfigDict(
        frozen=True, extra="forbid"
    )  # Make selector configuration immutable and reject unknown fields

    table_selector: str = Field(min_length=1)  # Identify schedule tables on the daily page
    club_table_selector: str = Field(
        min_length=1
    )  # Identify schedule tables on individual club pages
    date_header_class: str = Field(min_length=1)  # Identify rows containing a calendar date
    competition_header_class: str = Field(
        min_length=1
    )  # Identify rows containing a daily-page competition name
    time_selector: str = Field(min_length=1)  # Identify the kickoff-time element inside a match row
    home_selector: str = Field(min_length=1)  # Identify the home-team name inside a match row
    away_selector: str = Field(min_length=1)  # Identify the away-team name inside a match row
    club_competition_selector: str = Field(
        min_length=1
    )  # Identify the competition name on club schedule rows
    channels_container_selector: str = Field(
        min_length=1
    )  # Identify the container holding broadcast channels
    channel_item_selector: str = Field(
        min_length=1
    )  # Identify each individual channel inside its container
    start_date_selector: str = Field(min_length=1)  # Identify optional structured kickoff metadata


class ScheduleSourceConfig(
    BaseModel
):  # Validate private configuration for the current external schedule source
    model_config = ConfigDict(
        frozen=True, extra="forbid"
    )  # Reject accidental or unsupported operational configuration

    homepage_url: AnyHttpUrl  # Store the private daily-schedule URL without committing it to Git
    selectors: (
        ScheduleSourceSelectors  # Store the private selector profile used by the generic parser
    )


class ScrapedMatch(BaseModel):  # Represent one validated raw match returned by the parser
    model_config = ConfigDict(
        frozen=True
    )  # Prevent downstream code from mutating parsed source data accidentally

    kickoff_at: datetime  # Store the parsed kickoff timestamp canonically in UTC
    home_name_raw: str = Field(
        min_length=1, max_length=160
    )  # Preserve the source-provided home-team name
    away_name_raw: str = Field(
        min_length=1, max_length=160
    )  # Preserve the source-provided away-team name
    competition_raw: str = Field(
        min_length=1, max_length=160
    )  # Preserve the unnormalised competition name
    channels_raw: tuple[str, ...] = Field(
        min_length=1
    )  # Preserve each source-provided channel as a separate value
    source_kind: Literal[
        "daily_schedule", "club_schedule"
    ]  # Record which type of page produced this match
    source_reference: str | None = Field(
        default=None, max_length=2048
    )  # Preserve an optional runtime-only source reference

    @field_validator(
        "kickoff_at"
    )  # Validate every parsed kickoff before the object can leave the parser
    @classmethod  # Mark the validator as operating on the class rather than one existing model instance
    def ensure_timezone_aware_utc(
        cls, value: datetime
    ) -> datetime:  # Require timezone-aware kickoff values and canonicalise them to UTC
        if (
            value.tzinfo is None or value.utcoffset() is None
        ):  # Detect naive datetimes that would make scheduling ambiguous
            raise ValueError(
                "kickoff_at must be timezone-aware"
            )  # Reject ambiguous timestamps before they reach later pipeline stages

        return value.astimezone(
            UTC
        )  # Convert every valid kickoff to the application's canonical UTC representation
