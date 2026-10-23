"""Projects UI: projects, members and activity snapshots.

Revision ID: d127c8e8a441
Revises: c820dcf27a76
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd127c8e8a441'
down_revision = 'c820dcf27a76'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('showcase_url', sa.String(2048)),
        sa.Column('gitlab_url', sa.String(2048)),
        sa.Column('redmine_url', sa.String(2048)),
        sa.Column('gitlab_token_encrypted', sa.LargeBinary()),
        sa.Column('redmine_token_encrypted', sa.LargeBinary()),
        sa.Column('sprint_weeks', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('active_after_days', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('delayed_after_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('start_date', sa.Date()),
        sa.Column('deadline', sa.Date()),
        sa.Column('is_paused', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('archived_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('sprint_weeks BETWEEN 1 AND 12', name='ck_projects_sprint_weeks'),
        sa.CheckConstraint('active_after_days >= 0 AND delayed_after_days > active_after_days', name='ck_projects_activity_days'),
    )
    op.create_table(
        'project_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role', sa.String(100), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('project_id', 'email', name='uq_project_member_email'),
    )
    op.create_index('ix_project_members_project_id', 'project_members', ['project_id'])
    op.create_index('ix_project_members_user_id', 'project_members', ['user_id'])
    op.create_table(
        'project_activity',
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('last_gitlab_activity', sa.DateTime(timezone=True)),
        sa.Column('last_redmine_activity', sa.DateTime(timezone=True)),
        sa.Column('tasks_done', sa.Integer()),
        sa.Column('tasks_total', sa.Integer()),
        sa.Column('commits_per_day', sa.JSON()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('project_activity')
    op.drop_index('ix_project_members_user_id', table_name='project_members')
    op.drop_index('ix_project_members_project_id', table_name='project_members')
    op.drop_table('project_members')
    op.drop_table('projects')
