
import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from gitlab_service.app.database import SessionLocal
from gitlab_service.app.models import (
    GitLabCommit,
    GitLabConnection,
    GitLabOutboxEvent,
    GitLabProject,
)


with SessionLocal() as db:
    rows = db.execute(
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
    ).all()

    created = 0

    for commit, project, connection in rows:
        event_id = str(uuid4())

        event = {
            "event_id": event_id,
            "event_type": "gitlab.commit.created",
            "workspace_id": str(connection.workspace_id),
            "connection_id": str(connection.id),
            "project_id": project.external_project_id,
            "occurred_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "data": {
                "sha": commit.sha,
                "title": commit.title,
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

        db.add(
            GitLabOutboxEvent(
                id=uuid4(),
                topic="gitlab.commits",
                event_type="gitlab.commit.created",
                event_key=str(connection.workspace_id),
                payload=json.dumps(event),
            )
        )

        created += 1

    db.commit()

print("Подготовлено событий:", created)
