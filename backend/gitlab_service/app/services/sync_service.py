
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from gitlab_service.app.database import SessionLocal
from gitlab_service.app.models import (
    GitLabCommit,
    GitLabConnection,
    GitLabProject,
)
from gitlab_service.app.services.gitlab_service import GitLabService


def sync_commits(connection_id: UUID, external_project_id: int):
    with SessionLocal() as db:
        connection = db.get(GitLabConnection, connection_id)

        if connection is None:
            raise ValueError("GitLab connection not found")

        project = db.scalar(
            select(GitLabProject).where(
                GitLabProject.connection_id == connection_id,
                GitLabProject.external_project_id == external_project_id,
            )
        )

        if project is None:
            raise ValueError("GitLab project not found")

        # Временная тестовая конфигурация из .env
        gitlab = GitLabService()
        commits = gitlab.get_commits(external_project_id)

        saved = 0
        events = []

        for item in commits:
            sha = item["id"]

            existing = db.scalar(
                select(GitLabCommit).where(
                    GitLabCommit.project_id == project.id,
                    GitLabCommit.sha == sha,
                )
            )

            if existing is not None:
                continue

            stats = item.get("stats") or {}
            parent_ids = item.get("parent_ids") or []

            authored_at = item.get("authored_date")

            commit = GitLabCommit(
                project_id=project.id,
                sha=sha,
                author_name=item.get("author_name"),
                author_email=item.get("author_email"),
                title=item.get("title"),
                authored_at=(
                    datetime.fromisoformat(
                        authored_at.replace("Z", "+00:00")
                    )
                    if authored_at
                    else None
                ),
                additions=stats.get("additions", 0),
                deletions=stats.get("deletions", 0),
                is_merge=len(parent_ids) > 1,
            )

            db.add(commit)
            saved += 1

            events.append({
                "workspace_id": str(connection.workspace_id),
                "connection_id": str(connection.id),
                "project_id": external_project_id,
                "sha": sha,
                "author_name": item.get("author_name"),
                "authored_at": authored_at,
                "additions": stats.get("additions", 0),
                "deletions": stats.get("deletions", 0),
                "is_merge": len(parent_ids) > 1,
            })

        db.commit()

        return {
            "saved": saved,
            "events": events,
        }
