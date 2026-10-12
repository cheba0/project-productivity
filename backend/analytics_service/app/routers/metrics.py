
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from analytics_service.app.database import SessionLocal
from analytics_service.app.models import (
    ProjectMapping,
    AnalyticsMetric,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/projects")
def get_projects():
    with SessionLocal() as db:
        projects = db.scalars(select(ProjectMapping)).all()

        return [
            {
                "id": str(project.id),
                "name": project.name,
                "gitlab_project_id": project.gitlab_project_id,
                "redmine_project_id": project.redmine_project_id,
            }
            for project in projects
        ]


@router.get("/projects/{project_id}/metrics")
def get_project_metrics(project_id: UUID):
    with SessionLocal() as db:
        project = db.get(ProjectMapping, project_id)

        if project is None:
            raise HTTPException(
                status_code=404,
                detail="Project not found",
            )

        metrics = db.scalars(
            select(AnalyticsMetric).where(
                AnalyticsMetric.project_mapping_id == project_id
            )
        ).all()

        return {
            "project_id": str(project.id),
            "project_name": project.name,
            "metrics": {
                metric.metric_name: float(metric.metric_value)
                for metric in metrics
            },
        }



from datetime import date

from fastapi import Query

from analytics_service.app.services.metrics_service import (
    calculate_period_metrics,
)


@router.get("/projects/{project_id}/metrics/period")
def get_period_metrics(
    project_id: UUID,
    start_date: date = Query(...),
    end_date: date = Query(...),
):
    if start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date must not be after end_date",
        )

    try:
        metrics = calculate_period_metrics(
            project_mapping_id=project_id,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    return {
        "project_id": str(project_id),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "metrics": metrics,
    }



from analytics_service.app.services.developers_service import (
    get_developers_statistics,
)


@router.get("/projects/{project_id}/developers")
def get_project_developers(project_id: UUID):
    try:
        developers = get_developers_statistics(project_id)
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    return {
        "project_id": str(project_id),
        "developers": developers,
    }


from analytics_service.app.services.developer_metrics import (
    get_developer_metrics,
)

@router.get("/projects/{project_id}/developers/{gitlab_user_id}/metrics")
def get_developer_personal_metrics(
    project_id: UUID,
    gitlab_user_id: int,
):
    try:
        metrics = get_developer_metrics(
            project_mapping_id=project_id,
            gitlab_user_id=gitlab_user_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    return {
        "project_id": str(project_id),
        "gitlab_user_id": gitlab_user_id,
        "metrics": metrics,
    }


from analytics_service.app.models import (
    TaskCommitMapping,
    AnalyticsCommit,
    AnalyticsTask,
)


@router.get("/projects/{project_id}/task-commits")
def get_task_commits(project_id: UUID):
    with SessionLocal() as db:
        project = db.get(ProjectMapping, project_id)

        if project is None:
            raise HTTPException(
                status_code=404,
                detail="Project not found",
            )

        rows = db.execute(
            select(
                TaskCommitMapping,
                AnalyticsTask,
                AnalyticsCommit,
            )
            .join(
                AnalyticsTask,
                (AnalyticsTask.project_mapping_id
                 == TaskCommitMapping.project_mapping_id)
                & (AnalyticsTask.redmine_issue_id
                   == TaskCommitMapping.redmine_issue_id),
            )
            .join(
                AnalyticsCommit,
                (AnalyticsCommit.project_mapping_id
                 == TaskCommitMapping.project_mapping_id)
                & (AnalyticsCommit.sha
                   == TaskCommitMapping.gitlab_commit_sha),
            )
            .where(
                TaskCommitMapping.project_mapping_id == project_id
            )
        ).all()

        return {
            "project_id": str(project_id),
            "total": len(rows),
            "links": [
                {
                    "id": str(link.id),
                    "redmine_issue_id": link.redmine_issue_id,
                    "task_subject": task.subject,
                    "gitlab_commit_sha": link.gitlab_commit_sha,
                    "commit_title": commit.title,
                    "confirmed": link.confirmed,
                }
                for link, task, commit in rows
            ],
        }
