from datetime import datetime  # Import datetime for cache usage timestamps

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
)  # Import SQL column and constraint types
from sqlalchemy.orm import Mapped, mapped_column  # Import typed SQLAlchemy ORM mapping tools

from app.db.base import Base  # Import the common declarative model base
from app.models.mixins import TimestampMixin  # Import reusable creation and update timestamps


class NormalisationCache(
    TimestampMixin, Base
):  # Store reusable canonical resolutions for external names
    __tablename__ = (
        "normalisation_cache"  # Store normalisation results in one canonical database cache
    )
    __table_args__ = (  # Define uniqueness and validation rules for cached normalisations
        UniqueConstraint(
            "context", "lookup_key", name="uq_normalisation_cache_context_lookup"
        ),  # Prevent duplicate cached resolutions for the same contextual lookup
        CheckConstraint(  # Restrict normalisation entries to supported entity contexts
            "context IN ('club', 'competition', 'channel')",  # Accept only club, competition, or channel normalisation contexts
            name="valid_context",  # Give the context validation constraint a stable name
        ),  # Finish the normalisation-context constraint
        CheckConstraint(  # Restrict resolution methods to supported normalisation strategies
            "resolution_method IN ('rule', 'alias', 'manual', 'groq')",  # Record how the normalised value was produced
            name="valid_resolution_method",  # Give the resolution-method validation constraint a stable name
        ),  # Finish the resolution-method constraint
        CheckConstraint(
            "use_count >= 0", name="non_negative_use_count"
        ),  # Prevent invalid negative cache-use counters
    )  # Finish the normalisation-cache constraints

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Create the cache-entry primary key
    context: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # Store whether this entry resolves a club, competition, or channel
    raw_value: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Preserve the original external value
    lookup_key: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Store the deterministic normalised lookup key
    normalized_value: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Store the final canonical PT-PT display value
    resolution_method: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # Store which normalisation strategy produced the result
    provider_key: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )  # Store an optional generic schedule-provider context
    model_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )  # Store optional AI-model metadata for fallback resolutions
    needs_review: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Mark uncertain values for administrator review
    use_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # Count how often the cached result has been reused
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Record the most recent cache use
