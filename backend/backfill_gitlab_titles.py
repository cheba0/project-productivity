
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


def main():
    created = 0
    skipped = 0

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

        for commit, project, connection in rows:
            # Постоянный ID для одноразового обновления
            event_id = (
                f"backfill-title:{project.id}:{commit.sha}"
            )

            existing_events = db.scalars(
                select(GitLabOutboxEvent).where(
                    GitLabOutboxEvent.topic == "gitlab.commits"
                )
            ).all()

            already_exists = any(
                json.loads(row.payload).get("event_id") == event_id
                for row in existing_events
            )

            if already_exists:
                skipped += 1
                continue

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

    print("Создано событий:", created)
    print("Пропущено повторных событий:", skipped)


if __name__ == "__main__":
    main()
