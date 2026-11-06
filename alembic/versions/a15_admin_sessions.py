"""Add revocable administrator sessions and durable login throttles."""

import sqlalchemy as sa

from alembic import op

revision = "a15_admin_sessions"
down_revision = "e1a2c4340b1c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "admin_id",
            sa.Integer(),
            sa.ForeignKey("admin_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("password_version", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_admin_sessions_expires_at", "admin_sessions", ["expires_at"])
    op.create_table(
        "login_throttles",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_login_throttles_expires_at", "login_throttles", ["expires_at"])


def downgrade() -> None:
    op.drop_table("login_throttles")
    op.drop_table("admin_sessions")
