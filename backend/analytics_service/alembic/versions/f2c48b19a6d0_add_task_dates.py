"""Preserve task start/due dates for dashboard.

Revision ID: f2c48b19a6d0
Revises: e82c91a4f703
"""
from alembic import op
import sqlalchemy as sa

revision = "f2c48b19a6d0"
down_revision = "e82c91a4f703"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("analytics_tasks", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("analytics_tasks", sa.Column("due_date", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("analytics_tasks", "due_date")
    op.drop_column("analytics_tasks", "start_date")
