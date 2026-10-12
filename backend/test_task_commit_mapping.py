
from uuid import UUID

from sqlalchemy import select

from analytics_service.app.database import SessionLocal
from analytics_service.app.models import (
    AnalyticsCommit,
    TaskCommitMapping,
)
from analytics_service.app.services.task_commit_service import (
    link_commit_to_tasks,
)

PROJECT_ID = UUID(
    "ae24008f-9378-4245-ae0e-c91f6b27ae60"
)

SHA_PREFIX = "83ab25d7"

with SessionLocal() as db:
    commit = db.scalar(
        select(AnalyticsCommit).where(
            AnalyticsCommit.project_mapping_id == PROJECT_ID,
            AnalyticsCommit.sha.startswith(SHA_PREFIX),
        )
    )

    if commit is None:
        raise ValueError("Коммит не найден")

    print("Найден коммит:", commit.sha[:8])
    print("Исходное название:", commit.title)

    created = link_commit_to_tasks(
        db=db,
        project_mapping_id=PROJECT_ID,
        commit_sha=commit.sha,
        title="Add division function redmine:#5",
    )

    db.commit()

    print("Создано новых связей:", created)

    mappings = db.scalars(
        select(TaskCommitMapping).where(
            TaskCommitMapping.project_mapping_id == PROJECT_ID,
            TaskCommitMapping.gitlab_commit_sha == commit.sha,
        )
    ).all()

    for mapping in mappings:
        print(
            "Задача Redmine:", mapping.redmine_issue_id,
            "| Коммит:", mapping.gitlab_commit_sha[:8],
            "| Подтверждена:", mapping.confirmed,
        )
