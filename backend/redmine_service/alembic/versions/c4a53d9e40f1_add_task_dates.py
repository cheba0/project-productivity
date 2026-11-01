"""Preserve Redmine task dates for deadlines and sprint grouping.

Revision ID: c4a53d9e40f1
Revises: f19b789a33b0
"""
from alembic import op
import sqlalchemy as sa

revision = "c4a53d9e40f1"
down_revision = "f19b789a33b0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("redmine_issues", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("redmine_issues", sa.Column("due_date", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("redmine_issues", "due_date")
    op.drop_column("redmine_issues", "start_date")
