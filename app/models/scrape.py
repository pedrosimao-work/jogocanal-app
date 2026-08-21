from __future__ import (
    annotations,
)  # Allow relationship annotations to reference models from other modules

from datetime import datetime  # Import datetime for scrape lifecycle timestamps
from typing import TYPE_CHECKING  # Import TYPE_CHECKING for static-only imports

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)  # Import SQL column, foreign-key, and constraint types
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)  # Import typed SQLAlchemy ORM mapping tools

from app.db.base import Base  # Import the common declarative model base
from app.models.mixins import utc_now  # Import the shared timezone-aware UTC timestamp function

if TYPE_CHECKING:  # Import related models only during static analysis
    from app.models.admin_user import (
        AdminUser,
    )  # Import the administrator type associated with manual scrape jobs


class ScrapeRun(Base):  # Represent one complete execution of the schedule-ingestion pipeline
    __tablename__ = "scrape_runs"  # Store execution summaries in the scrape_runs table
    __table_args__ = (  # Define valid scraper execution states and counters
        CheckConstraint(
            "trigger IN ('scheduled', 'manual')", name="valid_trigger"
        ),  # Restrict run triggers to supported execution paths
        CheckConstraint(  # Restrict scraper runs to known lifecycle states
            "status IN ('running', 'completed', 'partial', 'failed')",  # Allow only the supported run statuses
            name="valid_status",  # Give the run-status constraint a stable name
        ),  # Finish the run-status constraint
        CheckConstraint(  # Prevent any scrape-run summary counter from becoming negative
            "sources_attempted >= 0 AND sources_successful >= 0 AND matches_found >= 0 AND matches_created >= 0 AND matches_updated >= 0 AND unknown_terms >= 0 AND error_count >= 0",  # Require every execution counter to remain zero or positive
            name="non_negative_counters",  # Give the counter-validation constraint a stable name
        ),  # Finish the counter-validation constraint
    )  # Finish the scrape-run table constraints

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Create the scrape-run primary key
    trigger: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # Record whether cron or an administrator requested the run
    status: Mapped[str] = mapped_column(
        String(20), default="running", nullable=False
    )  # Track the execution lifecycle state
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )  # Record when execution began
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Record when execution completed or failed
    sources_attempted: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # Count the schedule sources attempted during the run
    sources_successful: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # Count the sources successfully processed
    matches_found: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # Count the parsed matches discovered during the run
    matches_created: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # Count newly persisted matches
    matches_updated: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # Count existing matches updated from source data
    unknown_terms: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # Count names requiring fallback normalisation or review
    error_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # Count structured failures recorded during execution
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Store a concise execution summary for the administration dashboard

    events: Mapped[list[ScrapeRunEvent]] = (
        relationship(  # Link the run to its structured warnings and failures
            back_populates="run",  # Connect this relationship to ScrapeRunEvent.run
            cascade="all, delete-orphan",  # Remove event rows if their owning run is deliberately removed
        )
    )  # Finish the scrape-event relationship

    jobs: Mapped[list[ScrapeJob]] = relationship(
        back_populates="run"
    )  # Link manual jobs to the execution that eventually processed them


class ScrapeRunEvent(
    Base
):  # Represent one structured informational, warning, or error event from a scraper run
    __tablename__ = (
        "scrape_run_events"  # Store structured run events independently from plain-text log files
    )
    __table_args__ = (  # Define validation for event severity
        CheckConstraint(
            "level IN ('info', 'warning', 'error')", name="valid_level"
        ),  # Restrict events to supported severity levels
    )  # Finish the event-table constraints

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Create the event primary key
    run_id: Mapped[int] = mapped_column(
        ForeignKey("scrape_runs.id", ondelete="CASCADE"), nullable=False
    )  # Link the event to its owning scrape run
    stage: Mapped[str] = mapped_column(
        String(80), nullable=False
    )  # Identify which ingestion stage produced the event
    source_reference: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Store a safe generic reference to the affected source item
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # Store the event severity
    error_type: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )  # Store the optional exception or failure classification
    message: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Store the safe structured event message
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )  # Record when the event occurred

    run: Mapped[ScrapeRun] = relationship(
        back_populates="events"
    )  # Provide ORM access to the owning scrape run


class ScrapeJob(Base):  # Represent a durable request for a scraper execution
    __tablename__ = (
        "scrape_jobs"  # Store manual refresh requests independently from browser requests
    )
    __table_args__ = (  # Define valid durable-job lifecycle states
        CheckConstraint(  # Restrict jobs to supported execution states
            "status IN ('pending', 'running', 'completed', 'failed')",  # Allow only known job states
            name="valid_status",  # Give the job-status constraint a stable name
        ),  # Finish the job-status constraint
    )  # Finish the scrape-job table constraints

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Create the scrape-job primary key
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # Track the durable job lifecycle
    requested_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )  # Link manual requests to the administrator when available
    run_id: Mapped[int | None] = mapped_column(
        ForeignKey("scrape_runs.id", ondelete="SET NULL"), nullable=True
    )  # Link the job to the scrape run that processed it
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )  # Record when the refresh was requested
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Record when a worker claimed the job
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Record when processing completed or failed
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Preserve a safe failure explanation for unsuccessful jobs

    requested_by_admin: Mapped[AdminUser | None] = relationship(
        back_populates="requested_jobs"
    )  # Provide ORM access to the administrator who requested the job
    run: Mapped[ScrapeRun | None] = relationship(
        back_populates="jobs"
    )  # Provide ORM access to the execution that processed the job
