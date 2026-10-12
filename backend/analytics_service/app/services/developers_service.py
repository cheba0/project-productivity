
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from analytics_service.app.database import SessionLocal
from analytics_service.app.models import (
    ProjectMapping,
    UserMapping,
    AnalyticsTask,
    AnalyticsTimeEntry,
)


def get_developers_statistics(project_mapping_id: UUID):
    with SessionLocal() as db:
        project = db.get(ProjectMapping, project_mapping_id)

        if project is None:
            raise ValueError("Project not found")

        mappings = db.scalars(
            select(UserMapping).where(
                UserMapping.project_mapping_id == project_mapping_id,
                UserMapping.confirmed.is_(True),
            )
        ).all()

        tasks = db.scalars(
            select(AnalyticsTask).where(
                AnalyticsTask.project_mapping_id == project_mapping_id
            )
        ).all()

        time_entries = db.scalars(
            select(AnalyticsTimeEntry).where(
                AnalyticsTimeEntry.project_mapping_id == project_mapping_id
            )
        ).all()

        developers = []

        for mapping in mappings:
            user_tasks = [
                task for task in tasks
                if task.assignee_redmine_user_id
                == mapping.redmine_user_id
            ]

            user_time_entries = [
                entry for entry in time_entries
                if entry.redmine_user_id == mapping.redmine_user_id
            ]

            total_tasks = len(user_tasks)

            closed_tasks = sum(
                1 for task in user_tasks if task.is_closed
            )

            open_tasks = total_tasks - closed_tasks

            workload_hours = sum(
                (
                    task.estimated_hours or Decimal(0)
                    for task in user_tasks
                    if not task.is_closed
                ),
                Decimal(0),
            )

            spent_hours = sum(
                (
                    entry.hours or Decimal(0)
                    for entry in user_time_entries
                ),
                Decimal(0),
            )

            developers.append({
                "gitlab_user_id": mapping.gitlab_user_id,
                "redmine_user_id": mapping.redmine_user_id,
                "total_tasks": total_tasks,
                "closed_tasks": closed_tasks,
                "open_tasks": open_tasks,
                "workload_hours": float(workload_hours),
                "spent_hours": float(spent_hours),
            })

        return developers
