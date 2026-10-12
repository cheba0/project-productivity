
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func

from analytics_service.app.database import SessionLocal
from analytics_service.app.models import (
    ProjectMapping,
    AnalyticsTask,
    AnalyticsCommit,
    AnalyticsMetric,
)


def calculate_project_metrics(project_mapping_id: UUID):
    now = datetime.now(timezone.utc)

    # Период: с начала эпохи до текущего момента.
    # Для первого расчета используем накопительные показатели.
    period_start = datetime(1970, 1, 1, tzinfo=timezone.utc)
    period_end = datetime(9999, 12, 31, tzinfo=timezone.utc)

    with SessionLocal() as db:
        project = db.get(ProjectMapping, project_mapping_id)

        if project is None:
            raise ValueError("Project mapping not found")

        tasks = db.scalars(
            select(AnalyticsTask).where(
                AnalyticsTask.project_mapping_id == project_mapping_id
            )
        ).all()

        commits = db.scalars(
            select(AnalyticsCommit).where(
                AnalyticsCommit.project_mapping_id == project_mapping_id
            )
        ).all()

        total_tasks = len(tasks)
        closed_tasks = sum(1 for task in tasks if task.is_closed)
        open_tasks = total_tasks - closed_tasks

        completion_rate = (
            Decimal(closed_tasks) * 100 / Decimal(total_tasks)
            if total_tasks
            else Decimal(0)
        )

        estimated_hours = sum(
            (task.estimated_hours or Decimal(0) for task in tasks),
            Decimal(0),
        )

        task_spent_hours = sum(
            (task.spent_hours or Decimal(0) for task in tasks),
            Decimal(0),
        )

        total_commits = len(commits)
        non_merge_commits = sum(
            1 for commit in commits if not commit.is_merge
        )

        total_additions = sum(commit.additions or 0 for commit in commits)
        total_deletions = sum(commit.deletions or 0 for commit in commits)

        metrics = {
            "total_tasks": total_tasks,
            "closed_tasks": closed_tasks,
            "open_tasks": open_tasks,
            "completion_rate": completion_rate,
            "estimated_hours": estimated_hours,
            "task_spent_hours": task_spent_hours,
            "total_commits": total_commits,
            "non_merge_commits": non_merge_commits,
            "total_additions": total_additions,
            "total_deletions": total_deletions,
        }

        for metric_name, value in metrics.items():
            metric = db.scalar(
                select(AnalyticsMetric).where(
                    AnalyticsMetric.project_mapping_id == project_mapping_id,
                    AnalyticsMetric.metric_name == metric_name,
                    AnalyticsMetric.period_start == period_start,
                    AnalyticsMetric.period_end == period_end,
                )
            )

            if metric is None:
                metric = AnalyticsMetric(
                    project_mapping_id=project_mapping_id,
                    metric_name=metric_name,
                    period_start=period_start,
                    period_end=period_end,
                )
                db.add(metric)

            metric.metric_value = Decimal(str(value))
            metric.calculated_at = now

        db.commit()

        return metrics



from datetime import date, time, timedelta
from sqlalchemy import func

from analytics_service.app.models import AnalyticsTimeEntry


def calculate_period_metrics(
    project_mapping_id: UUID,
    start_date: date,
    end_date: date,
):
    if start_date > end_date:
        raise ValueError("Start date must not be after end date")

    start_dt = datetime.combine(
        start_date, time.min, tzinfo=timezone.utc
    )
    end_dt = datetime.combine(
        end_date + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )

    with SessionLocal() as db:
        project = db.get(ProjectMapping, project_mapping_id)

        if project is None:
            raise ValueError("Project mapping not found")

        closed_tasks = db.scalar(
            select(func.count(AnalyticsTask.id)).where(
                AnalyticsTask.project_mapping_id == project_mapping_id,
                AnalyticsTask.is_closed.is_(True),
                AnalyticsTask.closed_at >= start_dt,
                AnalyticsTask.closed_at < end_dt,
            )
        ) or 0

        commits = db.scalar(
            select(func.count(AnalyticsCommit.id)).where(
                AnalyticsCommit.project_mapping_id == project_mapping_id,
                AnalyticsCommit.is_merge.is_(False),
                AnalyticsCommit.authored_at >= start_dt,
                AnalyticsCommit.authored_at < end_dt,
            )
        ) or 0

        spent_hours = db.scalar(
            select(
                func.coalesce(
                    func.sum(AnalyticsTimeEntry.hours),
                    0,
                )
            ).where(
                AnalyticsTimeEntry.project_mapping_id == project_mapping_id,
                AnalyticsTimeEntry.spent_on >= start_date,
                AnalyticsTimeEntry.spent_on <= end_date,
            )
        )

        return {
            "closed_tasks": closed_tasks,
            "non_merge_commits": commits,
            "spent_hours": float(spent_hours),
        }
