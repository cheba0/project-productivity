"""Make GitLab optional in project mappings."""

from alembic import op
import sqlalchemy as sa


revision = "e82c91a4f703"
down_revision = "a1b004a249e5"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "project_mappings",
        "gitlab_connection_id",
        existing_type=sa.UUID(),
        nullable=True,
    )

    op.alter_column(
        "project_mappings",
        "gitlab_project_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        "project_mappings",
        "gitlab_connection_id",
        existing_type=sa.UUID(),
        nullable=False,
    )

    op.alter_column(
        "project_mappings",
        "gitlab_project_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
