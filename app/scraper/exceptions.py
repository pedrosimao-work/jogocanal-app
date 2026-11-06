class ScheduleSourceError(
    RuntimeError
):  # Define the common base exception for schedule-source failures
    pass  # Allow callers to catch all ingestion-specific failures through one exception type


class ScheduleSourceRequestError(
    ScheduleSourceError
):  # Represent an HTTP or network failure while retrieving schedule data
    pass  # Keep request failures distinct from parsing failures


class ScheduleParseError(
    ScheduleSourceError
):  # Represent HTML that cannot be safely interpreted as schedule data
    pass  # Prevent malformed source data from being silently treated as a successful empty result
