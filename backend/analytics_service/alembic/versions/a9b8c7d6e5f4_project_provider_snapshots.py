"""Store automatic project-level GitLab / Redmine snapshot feed.

Revision ID: a9b8c7d6e5f4
Revises: f2c48b19a6d0
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a9b8c7d6e5f4"
down_revision = "f2c48b19a6d0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "project_source_snapshots",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_project_source_snapshots_workspace_id",
        "project_source_snapshots", ["workspace_id"],
    )


def downgrade():
    op.drop_index("ix_project_source_snapshots_workspace_id",
                  table_name="project_source_snapshots")
    op.drop_table("project_source_snapshots")
