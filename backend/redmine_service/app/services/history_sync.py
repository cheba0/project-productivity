
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from redmine_service.app.services.redmine_service import RedmineService

from redmine_service.app.database import SessionLocal
from redmine_service.app.models import (
    RedmineConnection,
    RedmineIssue,
    RedmineUser,
    RedmineIssueStatusHistory,
)


def parse_datetime(value):
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def sync_status_history(connection_id: UUID):
    saved = 0
    updated = 0

    with SessionLocal() as db:
        connection = db.get(
            RedmineConnection,
            connection_id,
        )

        if connection is None:
            raise ValueError(
                "Redmine connection not found"
            )

        issues = db.scalars(
            select(RedmineIssue).where(
                RedmineIssue.connection_id == connection_id
            )
        ).all()

        # Пока используем тестовый Redmine API из .env.
        redmine = RedmineService()

        for issue in issues:
            response = redmine.get_issue(
                issue.external_issue_id
            )

            issue_data = response.get(
                "issue", response
            )

            journals = issue_data.get(
                "journals", []
            )

            for journal in journals:
                for detail in journal.get("details", []):
                    if (
                        detail.get("property") != "attr"
                        or detail.get("name") != "status_id"
                    ):
                        continue

                    history = db.scalar(
                        select(
                            RedmineIssueStatusHistory
                        ).where(
                            RedmineIssueStatusHistory.issue_id
                            == issue.id,
                            RedmineIssueStatusHistory.external_journal_id
                            == journal["id"],
                        )
                    )

                    author = journal.get("user") or {}
                    author_id = author.get("id")

                    local_user = None

                    if author_id is not None:
                        local_user = db.scalar(
                            select(RedmineUser).where(
                                RedmineUser.connection_id
                                == connection_id,
                                RedmineUser.external_user_id
                                == author_id,
                            )
                        )

                    old_value = detail.get("old_value")
                    new_value = detail.get("new_value")

                    values = {
                        "changed_by_user_id": (
                            local_user.id
                            if local_user is not None
                            else None
                        ),
                        "old_status_id": (
                            int(old_value)
                            if old_value not in (None, "")
                            else None
                        ),
                        "new_status_id": (
                            int(new_value)
                            if new_value not in (None, "")
                            else None
                        ),
                        "changed_at": parse_datetime(
                            journal.get("created_on")
                        ),
                    }

                    if history is None:
                        history = RedmineIssueStatusHistory(
                            issue_id=issue.id,
                            external_journal_id=journal["id"],
                            **values,
                        )
                        db.add(history)
                        saved += 1
                    else:
                        for field, value in values.items():
                            setattr(history, field, value)

                        updated += 1

        db.commit()

    return {
        "saved": saved,
        "updated": updated,
    }
