import json  # Import JSON decoding for the ignored private schedule-source configuration
from pathlib import Path  # Import Path for safe cross-platform configuration-file handling

from pydantic import ValidationError

from app.scraper.exceptions import ScheduleSourceError
from app.scraper.schemas import (
    ScheduleSourceConfig,  # Import the validated private configuration schema
)


def load_schedule_source_config(
    path: Path,
) -> ScheduleSourceConfig:  # Load and validate one private source-configuration file
    try:
        raw_data = json.loads(path.read_text(encoding="utf-8-sig"))
        return ScheduleSourceConfig.model_validate(raw_data)
    except (OSError, ValueError, ValidationError):
        raise ScheduleSourceError("Invalid schedule-source configuration") from None
