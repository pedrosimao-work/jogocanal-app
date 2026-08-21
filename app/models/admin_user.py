from __future__ import (
    annotations,
)  # Allow relationship annotations to reference models from other modules

from datetime import datetime  # Import datetime for administrator login timestamps
from typing import TYPE_CHECKING  # Import TYPE_CHECKING for static-only imports

from sqlalchemy import Boolean, DateTime, Integer, String  # Import SQL column types
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)  # Import typed SQLAlchemy ORM mapping tools

from app.db.base import Base  # Import the common declarative model base
from app.models.mixins import TimestampMixin  # Import reusable creation and update timestamps

if TYPE_CHECKING:  # Import related models only during static analysis
    from app.models.scrape import (
        ScrapeJob,
    )  # Import the scrape-job type requested by administrators


class AdminUser(TimestampMixin, Base):  # Represent a private JogoCanal administrator account
    __tablename__ = (
        "admin_users"  # Store administrator accounts separately from public application data
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )  # Create the administrator primary key
    email: Mapped[str] = mapped_column(
        String(254), unique=True, nullable=False
    )  # Store the unique administrator login email
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Store only the secure password hash rather than a plaintext password
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # Allow administrator access to be disabled without deleting the account
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Record the administrator's latest successful login

    requested_jobs: Mapped[list[ScrapeJob]] = relationship(
        back_populates="requested_by_admin"
    )  # Link the administrator to manually requested scrape jobs
