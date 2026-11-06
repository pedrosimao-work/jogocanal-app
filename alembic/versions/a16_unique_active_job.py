"""Reserve a unique slot for a pending or running manual update."""

import sqlalchemy as sa

from alembic import op

revision = "a16_unique_active_job"
down_revision = "a15_admin_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    active = connection.scalar(
        sa.text("SELECT count(*) FROM scrape_jobs WHERE status IN ('pending', 'running')")
    )
    if active and active > 1:
        raise RuntimeError("Resolve duplicate active scrape jobs before migration")
    op.add_column("scrape_jobs", sa.Column("active_slot", sa.Integer(), nullable=True))
    connection.execute(
        sa.text("UPDATE scrape_jobs SET active_slot=1 WHERE status IN ('pending', 'running')")
    )
    with op.batch_alter_table("scrape_jobs") as batch:
        batch.create_unique_constraint("uq_scrape_jobs_active_slot", ["active_slot"])
        batch.create_check_constraint(
            "active_job_slot",
            "(status IN ('pending', 'running') AND active_slot = 1 AND active_slot IS NOT NULL) OR (status IN ('completed', 'failed') AND active_slot IS NULL)",
        )


def downgrade() -> None:
    with op.batch_alter_table("scrape_jobs") as batch:
        batch.drop_constraint("uq_scrape_jobs_active_slot", type_="unique")
        batch.drop_constraint("active_job_slot", type_="check")
        batch.drop_column("active_slot")
