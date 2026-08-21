from __future__ import (
    annotations,
)  # Allow relationship type hints to reference models from other modules

from datetime import datetime  # Import datetime for match and source timestamps
from typing import TYPE_CHECKING  # Import TYPE_CHECKING for static-only related-model imports

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)  # Import SQL column, foreign-key, index, and constraint types
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)  # Import typed SQLAlchemy ORM mapping tools

from app.db.base import Base  # Import the common declarative model base
from app.models.mixins import utc_now  # Import the shared timezone-aware UTC timestamp function

if TYPE_CHECKING:  # Import related models only during static analysis
    from app.models.channel import Channel  # Import the channel type used by the association model
    from app.models.club import Club  # Import the recognised club type used by match relationships
    from app.models.competition import (
        Competition,
    )  # Import the competition type used by match relationships


class Match(Base):  # Represent one canonical televised football match
    __tablename__ = "matches"  # Store persisted matches in the matches table
    __table_args__ = (  # Define validation and query indexes for persisted matches
        CheckConstraint(  # Prevent one recognised club from being both sides of the same match
            "home_club_id IS NULL OR away_club_id IS NULL OR home_club_id <> away_club_id",  # Permit unknown clubs while rejecting identical recognised clubs
            name="different_home_and_away_clubs",  # Give the validation constraint a stable explicit name
        ),  # Finish the home-versus-away validation constraint
        Index(
            "ix_matches_kickoff_stale", "kickoff_at", "is_stale"
        ),  # Optimise chronological queries that exclude stale matches
    )  # Finish the match-table constraints and indexes

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Create the match primary key
    fingerprint: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )  # Store the deterministic deduplication fingerprint
    kickoff_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )  # Store the canonical kickoff timestamp in UTC
    home_club_id: Mapped[int | None] = mapped_column(
        ForeignKey("clubs.id", ondelete="SET NULL"), nullable=True
    )  # Link recognised home teams while allowing untracked teams
    away_club_id: Mapped[int | None] = mapped_column(
        ForeignKey("clubs.id", ondelete="SET NULL"), nullable=True
    )  # Link recognised away teams while allowing untracked teams
    home_name_raw: Mapped[str] = mapped_column(
        String(160), nullable=False
    )  # Preserve the original home-team name received from the source
    away_name_raw: Mapped[str] = mapped_column(
        String(160), nullable=False
    )  # Preserve the original away-team name received from the source
    home_name_display: Mapped[str] = mapped_column(
        String(160), nullable=False
    )  # Store the cleaned home-team name displayed by JogoCanal
    away_name_display: Mapped[str] = mapped_column(
        String(160), nullable=False
    )  # Store the cleaned away-team name displayed by JogoCanal
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"), nullable=False
    )  # Link the match to its canonical competition
    provider_key: Mapped[str] = mapped_column(
        String(80), nullable=False
    )  # Store the generic identifier of the schedule source
    source_status: Mapped[str | None] = mapped_column(
        String(40), nullable=True
    )  # Preserve an optional source-provided match status
    source_url: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Store the optional operational source reference outside public documentation
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )  # Record when JogoCanal first observed the match
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )  # Record when the match was most recently observed
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Store an optional update timestamp supplied by the source
    is_stale: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Mark matches that may no longer exist in successful source results
    needs_review: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Mark matches requiring manual normalisation or data review

    home_club: Mapped[Club | None] = relationship(  # Provide ORM access to the recognised home club
        back_populates="home_matches",  # Connect this relationship to Club.home_matches
        foreign_keys=[
            home_club_id
        ],  # Explicitly identify which club foreign key represents the home side
    )  # Finish the home-club relationship

    away_club: Mapped[Club | None] = relationship(  # Provide ORM access to the recognised away club
        back_populates="away_matches",  # Connect this relationship to Club.away_matches
        foreign_keys=[
            away_club_id
        ],  # Explicitly identify which club foreign key represents the away side
    )  # Finish the away-club relationship

    competition: Mapped[Competition] = relationship(
        back_populates="matches"
    )  # Provide ORM access to the canonical competition

    channel_links: Mapped[list[MatchChannel]] = (
        relationship(  # Link the match to all of its broadcast channels
            back_populates="match",  # Connect this relationship to MatchChannel.match
            cascade="all, delete-orphan",  # Remove association rows whenever their owning match is removed
        )
    )  # Finish the match-channel relationship


class MatchChannel(Base):  # Represent the many-to-many relationship between matches and channels
    __tablename__ = "match_channels"  # Store match/channel associations in the join table

    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), primary_key=True
    )  # Use the match foreign key as the first composite-primary-key column
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True
    )  # Use the channel foreign key as the second composite-primary-key column

    match: Mapped[Match] = relationship(
        back_populates="channel_links"
    )  # Provide ORM access to the associated match
    channel: Mapped[Channel] = relationship(
        back_populates="match_links"
    )  # Provide ORM access to the associated channel
