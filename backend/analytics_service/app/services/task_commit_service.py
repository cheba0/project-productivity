
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from analytics_service.app.models import (
    AnalyticsTask,
    TaskCommitMapping,
)


def extract_redmine_issue_ids(title: str | None) -> set[int]:
    if not title:
        return set()

    matches = re.findall(
        r"redmine:\s*#(\d+)\b",
        title,
        flags=re.IGNORECASE,
    )

    return {
        int(issue_id)
        for issue_id in matches
    }


def link_commit_to_tasks(
    db: Session,
    project_mapping_id: UUID,
    commit_sha: str,
    title: str | None,
) -> int:
    issue_ids = extract_redmine_issue_ids(title)

    if not issue_ids:
        return 0

    existing_issue_ids = set(
        db.scalars(
            select(AnalyticsTask.redmine_issue_id).where(
                AnalyticsTask.project_mapping_id
                == project_mapping_id,
                AnalyticsTask.redmine_issue_id.in_(issue_ids),
            )
        ).all()
    )

    created = 0

    for issue_id in existing_issue_ids:
        statement = (
            insert(TaskCommitMapping)
            .values(
                project_mapping_id=project_mapping_id,
                redmine_issue_id=issue_id,
                gitlab_commit_sha=commit_sha,
                confirmed=False,
            )
            .on_conflict_do_nothing(
                constraint="uq_task_commit_mapping"
            )
        )

        result = db.execute(statement)
        created += result.rowcount

    return created
