from sqlalchemy import select

from analytics_service.app.database import SessionLocal
from analytics_service.app.models import (
    AnalyticsCommit,
    ProjectMapping,
    UserMapping,
)


def get_developer_commits(project_mapping_id, author_email):
    with SessionLocal() as db:
        commits = db.scalars(
            select(AnalyticsCommit).where(
                AnalyticsCommit.project_mapping_id == project_mapping_id,
                AnalyticsCommit.author_email.ilike(author_email),
            )
        ).all()

        return [
            {
                "sha": commit.sha,
                "author_name": commit.author_name,
                "additions": commit.additions,
                "deletions": commit.deletions,
                "is_merge": commit.is_merge,
            }
            for commit in commits
        ]


def get_confirmed_user_mapping(project_mapping_id, gitlab_user_id):
    with SessionLocal() as db:
        mapping = db.scalar(
            select(UserMapping).where(
                UserMapping.project_mapping_id == project_mapping_id,
                UserMapping.gitlab_user_id == gitlab_user_id,
                UserMapping.confirmed.is_(True),
            )
        )

        if mapping is None:
            return None

        return {
            "gitlab_user_id": mapping.gitlab_user_id,
            "redmine_user_id": mapping.redmine_user_id,
        }