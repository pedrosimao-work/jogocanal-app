from __future__ import (
    annotations,
)  # Allow relationship type hints to reference models from other modules

from typing import TYPE_CHECKING  # Import TYPE_CHECKING for static-only model imports

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)  # Import SQL column, index, and constraint types
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)  # Import typed SQLAlchemy ORM mapping tools

from app.db.base import Base  # Import the common declarative model base
from app.models.mixins import (
    TimestampMixin,
)  # Import reusable creation and update timestamp columns

if TYPE_CHECKING:  # Import related models only for static analysis
    from app.models.club import Club  # Import the club type used by league memberships


class League(
    TimestampMixin, Base
):  # Represent a football league independently from any particular season
    __tablename__ = "leagues"  # Store league records in the leagues table
    __table_args__ = (  # Define database-level validation for league records
        CheckConstraint(
            "tier > 0", name="positive_tier"
        ),  # Require every league tier to be a positive integer
    )  # Finish the league constraints

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Create the league primary key
    name: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False
    )  # Store the canonical league name
    slug: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False
    )  # Store the stable URL-safe league identifier
    tier: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )  # Store the league's level within the domestic pyramid
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # Identify leagues currently used by the application

    memberships: Mapped[list[LeagueMembership]] = (
        relationship(  # Link the league to club memberships across seasons
            back_populates="league",  # Connect this relationship to LeagueMembership.league
            cascade="all, delete-orphan",  # Remove memberships if the owning league record is deliberately removed
        )
    )  # Finish the league-membership relationship


class LeagueMembership(
    TimestampMixin, Base
):  # Represent one club's membership in one league during one season
    __tablename__ = "league_memberships"  # Store historical and current memberships separately from club identity
    __table_args__ = (  # Define relational rules and query indexes for memberships
        UniqueConstraint(
            "club_id", "season", name="uq_league_memberships_club_season"
        ),  # Prevent one club from belonging to two tracked leagues in the same season
        CheckConstraint(
            "display_order > 0", name="positive_display_order"
        ),  # Require public league ordering to start from a positive position
        Index(
            "ix_league_memberships_league_season_order", "league_id", "season", "display_order"
        ),  # Optimise season-specific ordered league listings
    )  # Finish the membership-table rules

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Create the membership primary key
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )  # Link the membership to its club
    league_id: Mapped[int] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False
    )  # Link the membership to its league
    season: Mapped[str] = mapped_column(
        String(9), nullable=False
    )  # Store the football season using the YYYY/YYYY representation
    display_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )  # Store the club's deterministic display position within the league
    is_confirmed: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # Allow unresolved season places to remain explicitly unconfirmed

    club: Mapped[Club] = relationship(
        back_populates="memberships"
    )  # Provide ORM access to the membership's club
    league: Mapped[League] = relationship(
        back_populates="memberships"
    )  # Provide ORM access to the membership's league
