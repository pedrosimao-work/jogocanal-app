from datetime import UTC, datetime  # Import timezone-aware datetime tools for UTC timestamps

from sqlalchemy import DateTime  # Import SQLAlchemy's datetime column type
from sqlalchemy.orm import Mapped, mapped_column  # Import typed ORM mapping tools


def utc_now() -> datetime:  # Return the current timestamp using timezone-aware UTC
    return datetime.now(UTC)  # Generate the current UTC datetime


class TimestampMixin:  # Provide reusable creation and update timestamps to ORM models
    created_at: Mapped[datetime] = (
        mapped_column(  # Store when the database record was first created
            DateTime(timezone=True),  # Store a timezone-aware datetime value
            default=utc_now,  # Generate the timestamp when a new ORM object is persisted
            nullable=False,  # Require every record using this mixin to have a creation timestamp
        )
    )  # Finish the created-at column configuration

    updated_at: Mapped[datetime] = (
        mapped_column(  # Store when the database record was most recently changed
            DateTime(timezone=True),  # Store a timezone-aware datetime value
            default=utc_now,  # Set an initial update timestamp when the record is created
            onupdate=utc_now,  # Refresh the timestamp whenever SQLAlchemy updates the record
            nullable=False,  # Require every record using this mixin to have an update timestamp
        )
    )  # Finish the updated-at column configuration
