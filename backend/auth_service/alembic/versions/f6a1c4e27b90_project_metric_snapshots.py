"""Store GitLab/Redmine snapshots for project dashboards.
Revision ID: f6a1c4e27b90
Revises: e3281d10b152
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f6a1c4e27b90"
down_revision = "e3281d10b152"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "project_metric_snapshots",
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("source_hash", sa.String(64)),
        sa.Column("period_start", sa.Date()),
        sa.Column("period_end", sa.Date()),
        sa.Column("payload", postgresql.JSONB()),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(500)),
    )


def downgrade():
    op.drop_table("project_metric_snapshots")
