from datetime import (
    datetime,
)  # Import datetime so each private mapping records when it was verified

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
)  # Import Pydantic validation tools for private mapping files


class SourceMappingSeed(BaseModel):  # Validate one private operational club-to-source mapping
    model_config = ConfigDict(
        extra="forbid"
    )  # Reject unexpected fields so mapping-file mistakes are detected immediately

    club_slug: str = Field(min_length=1, max_length=120)  # Identify the canonical JogoCanal club
    provider_key: str = Field(
        default="primary_schedule", min_length=1, max_length=80
    )  # Use a generic internal provider identifier
    source_slug: str = Field(
        min_length=1, max_length=255
    )  # Store the private provider-specific club identifier
    source_url: AnyHttpUrl  # Require the private operational source reference to be a valid HTTP or HTTPS URL
    verified_at: datetime  # Record when this mapping was manually confirmed against the live source
