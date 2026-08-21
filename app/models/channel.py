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
    from app.models.match import (
        MatchChannel,
    )  # Import the association-model type linking channels to matches


class Channel(TimestampMixin, Base):  # Represent one canonical television or streaming channel
    __tablename__ = "channels"  # Store canonical channels in the channels table

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Create the channel primary key
    name: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False
    )  # Store the canonical channel display name
    slug: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False
    )  # Store the stable channel identifier
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # Allow obsolete channels to remain historically available

    match_links: Mapped[list[MatchChannel]] = (
        relationship(  # Link the channel to matches through the association model
            back_populates="channel",  # Connect this relationship to MatchChannel.channel
            cascade="all, delete-orphan",  # Remove association rows when the owning channel is deliberately removed
        )
    )  # Finish the match-channel relationship
