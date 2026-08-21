from __future__ import (
    annotations,
)  # Allow relationship annotations to reference models declared elsewhere

from typing import TYPE_CHECKING  # Import TYPE_CHECKING for static-only imports

from sqlalchemy import Boolean, Integer, String  # Import SQL column types
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)  # Import typed SQLAlchemy ORM mapping tools

from app.db.base import Base  # Import the common declarative model base
from app.models.mixins import TimestampMixin  # Import reusable creation and update timestamps

if TYPE_CHECKING:  # Import related models only during static analysis
    from app.models.match import Match  # Import the match type used by the competition relationship


class Competition(TimestampMixin, Base):  # Represent a canonical football competition
    __tablename__ = "competitions"  # Store canonical competitions in their own table

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Create the competition primary key
    name: Mapped[str] = mapped_column(
        String(160), unique=True, nullable=False
    )  # Store the canonical display name
    slug: Mapped[str] = mapped_column(
        String(160), unique=True, nullable=False
    )  # Store the URL-safe competition identifier
    country_code: Mapped[str | None] = mapped_column(
        String(2), nullable=True
    )  # Store the optional two-letter country code
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # Allow historical competitions to remain without being treated as active

    matches: Mapped[list[Match]] = relationship(
        back_populates="competition"
    )  # Link the competition to persisted matches
