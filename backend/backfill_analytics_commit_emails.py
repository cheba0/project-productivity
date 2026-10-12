from sqlalchemy import select

from gitlab_service.app.database import (
    SessionLocal as GitLabSession,
)
from gitlab_service.app.models import (
    GitLabCommit,
    GitLabProject,
    GitLabConnection,
)

from analytics_service.app.database import (
    SessionLocal as AnalyticsSession,
)
from analytics_service.app.models import (
    AnalyticsCommit,
    ProjectMapping,
)


def main():
    updated = 0
    missing = 0

    with GitLabSession() as gitlab_db:
        rows = gitlab_db.execute(
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
                GitLabProject.connection_id
                == GitLabConnection.id,
            )
        ).all()

        with AnalyticsSession() as analytics_db:
            for commit, project, connection in rows:
                mapping = analytics_db.scalar(
                    select(ProjectMapping).where(
                        ProjectMapping.workspace_id
                        == connection.workspace_id,
                        ProjectMapping.gitlab_connection_id
                        == connection.id,
                        ProjectMapping.gitlab_project_id
                        == project.external_project_id,
                    )
                )

                if mapping is None:
                    missing += 1
                    continue

                analytics_commit = analytics_db.scalar(
                    select(AnalyticsCommit).where(
                        AnalyticsCommit.project_mapping_id
                        == mapping.id,
                        AnalyticsCommit.sha == commit.sha,
                    )
                )

                if analytics_commit is None:
                    missing += 1
                    continue

                if (
                    commit.author_email
                    and analytics_commit.author_email
                    != commit.author_email
                ):
                    analytics_commit.author_email = (
                        commit.author_email
                    )
                    updated += 1

            analytics_db.commit()

    print("Обновлено коммитов:", updated)
    print("Не найдено соответствий:", missing)


if __name__ == "__main__":
    main()