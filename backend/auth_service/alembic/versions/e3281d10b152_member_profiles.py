"""Project member profiles
Revision ID: e3281d10b152
Revises: d127c8e8a441
"""
from alembic import op
import sqlalchemy as sa
revision = 'e3281d10b152'
down_revision = 'd127c8e8a441'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('project_member_profiles',
        sa.Column('member_id', sa.UUID(), sa.ForeignKey('project_members.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('phone', sa.String(50)), sa.Column('telegram', sa.String(100)),
        sa.Column('gitlab_profile_url', sa.String(2048)), sa.Column('redmine_profile_url', sa.String(2048)),
        sa.Column('gitlab_email', sa.String(255)), sa.Column('redmine_user_id', sa.Integer()))


def downgrade():
    op.drop_table('project_member_profiles')
