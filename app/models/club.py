from __future__ import (
    annotations,
)  # Allow relationship type hints to reference models defined in other modules

from datetime import datetime  # Import datetime for source-verification timestamps
from typing import (
    TYPE_CHECKING,
)  # Import TYPE_CHECKING so related models are imported only for static analysis

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)  # Import SQL column and constraint types
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)  # Import typed SQLAlchemy ORM mapping tools

from app.db.base import Base  # Import the common declarative model base
from app.models.mixins import (
    TimestampMixin,
)  # Import reusable creation and update timestamp columns

if TYPE_CHECKING:  # Import related models only while static type checking is running
    from app.models.league import (
        LeagueMembership,
    )  # Import the league-membership type used by Club relationships
    from app.models.match import Match  # Import the match type used by Club relationships


class Club(TimestampMixin, Base):  # Represent the permanent identity of a football club
    __tablename__ = "clubs"  # Store club records in the clubs table

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )  # Create the internal integer primary key
    name: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False
    )  # Store the canonical Portuguese club name
    slug: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False
    )  # Store the stable URL-safe club identifier
    short_name: Mapped[str] = mapped_column(
        String(80), nullable=False
    )  # Store the compact club name used in constrained interfaces
    crest_path: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Store the optional local crest asset path
    is_tracked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )  # Identify clubs with dedicated JogoCanal tracking
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )  # Identify clubs that remain active application records

    memberships: Mapped[list[LeagueMembership]] = (
        relationship(  # Link the club to its season-specific league memberships
            back_populates="club",  # Connect this relationship to LeagueMembership.club
            cascade="all, delete-orphan",  # Remove membership rows if the owning club record is deliberately removed
        )
    )  # Finish the league-membership relationship

    aliases: Mapped[list[ClubAlias]] = (
        relationship(  # Link the club to alternative names recognised by normalisation
            back_populates="club",  # Connect this relationship to ClubAlias.club
            cascade="all, delete-orphan",  # Remove aliases if the owning club record is deliberately removed
        )
    )  # Finish the alias relationship

    source_mappings: Mapped[list[ClubSourceMapping]] = (
        relationship(  # Link the club to its external schedule-source mappings
            back_populates="club",  # Connect this relationship to ClubSourceMapping.club
            cascade="all, delete-orphan",  # Remove source mappings if the owning club record is deliberately removed
        )
    )  # Finish the source-mapping relationship

    home_matches: Mapped[list[Match]] = (
        relationship(  # Link the club to matches where it is recognised as the home club
            back_populates="home_club",  # Connect this relationship to Match.home_club
            foreign_keys="Match.home_club_id",  # Explicitly identify the home-club foreign key
        )
    )  # Finish the home-match relationship

    away_matches: Mapped[list[Match]] = (
        relationship(  # Link the club to matches where it is recognised as the away club
            back_populates="away_club",  # Connect this relationship to Match.away_club
            foreign_keys="Match.away_club_id",  # Explicitly identify the away-club foreign key
        )
    )  # Finish the away-match relationship


class ClubAlias(
    TimestampMixin, Base
):  # Store alternative names that resolve deterministically to one canonical club
    __tablename__ = "club_aliases"  # Store club aliases in their own relational table
    __table_args__ = (  # Define additional relational constraints for club aliases
        UniqueConstraint(
            "normalized_alias", name="uq_club_aliases_normalized_alias"
        ),  # Prevent one normalised alias from resolving to multiple clubs
    )  # Finish the alias-table constraints

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Create the alias primary key
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )  # Link the alias to its canonical club
    alias: Mapped[str] = mapped_column(
        String(160), nullable=False
    )  # Store the original recognised alias
    normalized_alias: Mapped[str] = mapped_column(
        String(160), nullable=False
    )  # Store the deterministic lookup representation of the alias

    club: Mapped[Club] = relationship(
        back_populates="aliases"
    )  # Provide ORM access to the canonical club


class ClubSourceMapping(
    TimestampMixin, Base
):  # Store private operational mappings between clubs and an external schedule source
    __tablename__ = (
        "club_source_mappings"  # Store source mappings separately from canonical club identity
    )
    __table_args__ = (  # Define uniqueness rules for source mappings
        UniqueConstraint(
            "club_id", "provider_key", name="uq_club_source_mappings_club_provider"
        ),  # Allow one mapping per club and schedule provider
    )  # Finish the source-mapping constraints

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )  # Create the source-mapping primary key
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )  # Link the mapping to its canonical club
    provider_key: Mapped[str] = mapped_column(
        String(80), nullable=False
    )  # Store a generic internal identifier for the schedule provider
    source_slug: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Store the provider-specific club identifier
    source_url: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Store the operational source URL in database data rather than public documentation
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Record when the mapping was last manually verified
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Record the most recent successful use of the mapping
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # Allow obsolete mappings to be disabled without deleting their history

    club: Mapped[Club] = relationship(
        back_populates="source_mappings"
    )  # Provide ORM access to the canonical club
