from uuid import uuid4

from sqlalchemy import select

from gitlab_service.app.database import (
    SessionLocal as GitLabSession,
)
from gitlab_service.app.models import (
    GitLabCommit,
    GitLabProject,
    GitLabConnection,
)

from analytics_service.app.services.kafka_consumer import (
    save_commit_event,
)


with GitLabSession() as db:
    row = db.execute(
        select(
            GitLabCommit,
            GitLabProject,
            GitLabConnection,
        )
        .join(
            GitLabProject,
            GitLabCommit.project_id == GitLabProject.id,
        )
        .join(
            GitLabConnection,
            GitLabProject.connection_id == GitLabConnection.id,
        )
        .limit(1)
    ).first()

    if row is None:
        raise RuntimeError("Коммиты GitLab не найдены")

    commit, project, connection = row

    event = {
        "event_id": str(uuid4()),
        "event_type": "gitlab.commit.created",
        "workspace_id": str(connection.workspace_id),
        "connection_id": str(connection.id),
        "project_id": project.external_project_id,
        "data": {
            "sha": commit.sha,
            "author_name": commit.author_name,
            "author_email": commit.author_email,
            "authored_at": (
                commit.authored_at.isoformat()
                if commit.authored_at
                else None
            ),
            "additions": commit.additions,
            "deletions": commit.deletions,
            "is_merge": commit.is_merge,
        },
    }

result = save_commit_event(event)

print("Результат:", result)
print("SHA:", event["data"]["sha"])
print("Email:", event["data"]["author_email"])