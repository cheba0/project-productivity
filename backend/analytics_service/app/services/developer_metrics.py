
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from analytics_service.app.database import SessionLocal
from analytics_service.app.models import (
    AnalyticsCommit,
    AnalyticsTask,
    AnalyticsTimeEntry,
    ProjectMapping,
    UserMapping,
)


def get_developer_metrics(
    project_mapping_id: UUID,
    gitlab_user_id: int,
):
    with SessionLocal() as db:
        project = db.get(ProjectMapping, project_mapping_id)

        if project is None:
            raise ValueError("Project not found")

        mapping = db.scalar(
            select(UserMapping).where(
                UserMapping.project_mapping_id == project_mapping_id,
                UserMapping.gitlab_user_id == gitlab_user_id,
                UserMapping.confirmed.is_(True),
            )
        )

        if mapping is None:
            raise ValueError(
                "Подтверждённое соответствие пользователей не найдено"
            )

        redmine_user_id = mapping.redmine_user_id
        author_email = mapping.gitlab_author_email

        tasks = db.scalars(
            select(AnalyticsTask).where(
                AnalyticsTask.project_mapping_id == project_mapping_id,
                AnalyticsTask.assignee_redmine_user_id == redmine_user_id,
            )
        ).all()

        time_entries = db.scalars(
            select(AnalyticsTimeEntry).where(
                AnalyticsTimeEntry.project_mapping_id == project_mapping_id,
                AnalyticsTimeEntry.redmine_user_id == redmine_user_id,
            )
        ).all()

        commits = []

        if author_email:
            commits = db.scalars(
                select(AnalyticsCommit).where(
                    AnalyticsCommit.project_mapping_id == project_mapping_id,
                    AnalyticsCommit.author_email.ilike(author_email),
                )
            ).all()

        closed_tasks = sum(
            1 for task in tasks if task.is_closed
        )

        logged_hours = sum(
            (entry.hours for entry in time_entries),
            Decimal("0"),
        )

        return {
            "gitlab_user_id": gitlab_user_id,
            "redmine_user_id": redmine_user_id,
            "assigned_tasks": len(tasks),
            "closed_tasks": closed_tasks,
            "open_tasks": len(tasks) - closed_tasks,
            "total_commits": len(commits),
            "non_merge_commits": sum(
                1 for commit in commits if not commit.is_merge
            ),
            "logged_hours": float(logged_hours),
            "gitlab_email_linked": bool(author_email),
        }
