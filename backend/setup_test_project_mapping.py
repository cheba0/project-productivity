
from uuid import UUID

from sqlalchemy import select

from analytics_service.app.database import SessionLocal
from analytics_service.app.models import ProjectMapping


WORKSPACE_ID = UUID("11111111-1111-4111-8111-111111111111")
GITLAB_CONNECTION_ID = UUID("33333333-3333-4333-8333-333333333333")
REDMINE_CONNECTION_ID = UUID("44444444-4444-4444-8444-444444444444")


with SessionLocal() as db:
    mapping = db.scalar(
        select(ProjectMapping).where(
            ProjectMapping.workspace_id == WORKSPACE_ID,
            ProjectMapping.gitlab_connection_id == GITLAB_CONNECTION_ID,
            ProjectMapping.gitlab_project_id == 87303510,
        )
    )

    if mapping is None:
        mapping = ProjectMapping(
            workspace_id=WORKSPACE_ID,
            gitlab_connection_id=GITLAB_CONNECTION_ID,
            gitlab_project_id=87303510,
            redmine_connection_id=REDMINE_CONNECTION_ID,
            redmine_project_id=1,
            name="Productivity Test Calculator",
        )
        db.add(mapping)
        db.commit()

print("Соответствие проектов создано.")
