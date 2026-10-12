
from uuid import UUID

from sqlalchemy import select

from redmine_service.app.database import SessionLocal
from redmine_service.app.models import (
    RedmineConnection,
    RedmineProject,
    RedmineUser,
    RedmineStatus,
    RedmineIssue,
    RedmineTimeEntry,
    RedmineOutboxEvent,
)
from redmine_service.app.services.sync_service import add_outbox


CONNECTION_ID = UUID(
    "44444444-4444-4444-8444-444444444444"
)


def iso(value):
    return value.isoformat() if value is not None else None


def decimal_str(value):
    return str(value) if value is not None else None


def backfill():
    added_issues = 0
    added_entries = 0

    with SessionLocal() as db:
        connection = db.get(RedmineConnection, CONNECTION_ID)

        if connection is None:
            raise ValueError("Redmine connection not found")

        projects = {
            p.id: p.external_project_id
            for p in db.scalars(
                select(RedmineProject).where(
                    RedmineProject.connection_id == CONNECTION_ID
                )
            )
        }

        users = {
            u.id: u.external_user_id
            for u in db.scalars(
                select(RedmineUser).where(
                    RedmineUser.connection_id == CONNECTION_ID
                )
            )
        }

        statuses = {
            s.id: s.external_status_id
            for s in db.scalars(
                select(RedmineStatus).where(
                    RedmineStatus.connection_id == CONNECTION_ID
                )
            )
        }

        issues = db.scalars(
            select(RedmineIssue).where(
                RedmineIssue.connection_id == CONNECTION_ID
            )
        ).all()

        issue_ids = {
            issue.id: issue.external_issue_id
            for issue in issues
        }

        existing = set()

        events = db.scalars(
            select(RedmineOutboxEvent).where(
                RedmineOutboxEvent.connection_id == CONNECTION_ID
            )
        ).all()

        for event in events:
            data = (event.payload or {}).get("data") or {}
            external_id = data.get("id")

            if external_id is not None:
                existing.add(
                    (event.event_type, str(external_id))
                )

        for issue in issues:
            key = (
                "redmine.issue.upserted",
                str(issue.external_issue_id),
            )

            if key in existing:
                continue

            add_outbox(
                db,
                connection,
                key[0],
                {
                    "id": issue.external_issue_id,
                    "project_id": projects[issue.project_id],
                    "assignee_external_id": users.get(
                        issue.assignee_id
                    ),
                    "status_external_id": statuses[
                        issue.status_id
                    ],
                    "subject": issue.subject,
                    "description": issue.description,
                    "priority_name": issue.priority_name,
                    "tracker_name": issue.tracker_name,
                    "estimated_hours": decimal_str(
                        issue.estimated_hours
                    ),
                    "spent_hours": decimal_str(
                        issue.spent_hours
                    ),
                    "done_ratio": issue.done_ratio,
                    "created_at": iso(issue.created_at),
                    "updated_at": iso(issue.updated_at),
                    "closed_at": iso(issue.closed_at),
                },
            )

            existing.add(key)
            added_issues += 1

        entries = db.scalars(
            select(RedmineTimeEntry).where(
                RedmineTimeEntry.connection_id == CONNECTION_ID
            )
        ).all()

        for entry in entries:
            key = (
                "redmine.time_entry.upserted",
                str(entry.external_entry_id),
            )

            if key in existing:
                continue

            add_outbox(
                db,
                connection,
                key[0],
                {
                    "id": entry.external_entry_id,
                    "project_id": projects[entry.project_id],
                    "issue_external_id": issue_ids.get(
                        entry.issue_id
                    ),
                    "user_external_id": users[entry.user_id],
                    "hours": decimal_str(entry.hours),
                    "activity_name": entry.activity_name,
                    "comments": entry.comments,
                    "spent_on": iso(entry.spent_on),
                },
            )

            existing.add(key)
            added_entries += 1

        db.commit()

    print("Первоначальная загрузка завершена")
    print("Добавлено событий задач:", added_issues)
    print("Добавлено событий трудозатрат:", added_entries)


if __name__ == "__main__":
    backfill()
