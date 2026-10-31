
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import inspect

from sqlalchemy import select

from redmine_service.app.services.redmine_service import RedmineService

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


def parse_datetime(value):
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def parse_decimal(value):
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"))


def parse_date(value):
    return date.fromisoformat(str(value)[:10]) if value else None



def has_changes(obj):
    state = inspect(obj)
    if state.pending:
        return True
    return any(attr.history.has_changes() for attr in state.attrs)


def add_outbox(db, connection, event_type, data):
    db.add(RedmineOutboxEvent(
        id=uuid4(),
        connection_id=connection.id,
        event_type=event_type,
        payload={
            "event_type": event_type,
            "workspace_id": str(connection.workspace_id),
            "connection_id": str(connection.id),
            "data": data,
        },
    ))


def sync_redmine(
    connection_id: UUID,
    external_project_id: int,
):
    # Проверяем подключение до обращения к API.
    with SessionLocal() as db:
        connection = db.get(
            RedmineConnection,
            connection_id,
        )

        if connection is None:
            raise ValueError(
                "Redmine connection not found"
            )

    # Получаем данные из Redmine API.
    # Пока используется тестовый токен из .env.
    redmine = RedmineService()

    projects = redmine.get_projects()
    users = redmine.get_users()
    statuses = redmine.get_statuses()
    issues = redmine.get_issues(
        project_id=external_project_id
    )
    entries = redmine.get_time_entries(
        project_id=external_project_id
    )

    with SessionLocal() as db:
        # 1. Находим подключение.
        connection = db.get(
            RedmineConnection,
            connection_id,
        )

        if connection is None:
            raise ValueError(
                "Redmine connection not found"
            )

        # 2. Находим проект в ответе API.
        project_data = next(
            (
                item
                for item in projects
                if item["id"] == external_project_id
            ),
            None,
        )

        if project_data is None:
            raise ValueError(
                "Redmine project not found"
            )

        # 3. Сохраняем или обновляем проект.
        project = db.scalar(
            select(RedmineProject).where(
                RedmineProject.connection_id
                == connection_id,
                RedmineProject.external_project_id
                == external_project_id,
            )
        )

        if project is None:
            project = RedmineProject(
                connection_id=connection_id,
                external_project_id=external_project_id,
                name=project_data["name"],
                identifier=project_data.get(
                    "identifier"
                ),
                description=project_data.get(
                    "description"
                ),
            )

            db.add(project)
        else:
            project.name = project_data["name"]
            project.identifier = project_data.get(
                "identifier"
            )
            project.description = project_data.get(
                "description"
            )

        db.flush()

        # 4. Сохраняем пользователей.
        user_map = {}

        for item in users:
            user = db.scalar(
                select(RedmineUser).where(
                    RedmineUser.connection_id
                    == connection_id,
                    RedmineUser.external_user_id
                    == item["id"],
                )
            )

            if user is None:
                user = RedmineUser(
                    connection_id=connection_id,
                    external_user_id=item["id"],
                    login=item.get("login"),
                    firstname=item.get("firstname"),
                    lastname=item.get("lastname"),
                    email=item.get("mail"),
                )

                db.add(user)
            else:
                user.login = item.get("login")
                user.firstname = item.get(
                    "firstname"
                )
                user.lastname = item.get(
                    "lastname"
                )
                user.email = item.get("mail")

            db.flush()
            user_map[item["id"]] = user.id

        # 5. Сохраняем статусы.
        status_map = {}

        for item in statuses:
            status = db.scalar(
                select(RedmineStatus).where(
                    RedmineStatus.connection_id
                    == connection_id,
                    RedmineStatus.external_status_id
                    == item["id"],
                )
            )

            if status is None:
                status = RedmineStatus(
                    connection_id=connection_id,
                    external_status_id=item["id"],
                    name=item["name"],
                    is_closed=item.get(
                        "is_closed",
                        False,
                    ),
                )

                db.add(status)
            else:
                status.name = item["name"]
                status.is_closed = item.get(
                    "is_closed",
                    False,
                )

            db.flush()
            status_map[item["id"]] = status.id

        # 6. Сохраняем задачи. Redmine status IDs are installation-specific.
        status_details = {status["id"]: status for status in statuses}
        issue_map = {}

        for item in issues:
            issue = db.scalar(
                select(RedmineIssue).where(
                    RedmineIssue.connection_id
                    == connection_id,
                    RedmineIssue.external_issue_id
                    == item["id"],
                )
            )

            assignee_data = (
                item.get("assigned_to") or {}
            )

            status_data = (
                item.get("status") or {}
            )

            assignee_id = user_map.get(
                assignee_data.get("id")
            )

            status_id = status_map.get(
                status_data.get("id")
            )

            if status_id is None:
                raise ValueError(
                    "Не найден статус для задачи "
                    f"{item['id']}"
                )

            if (
                assignee_data.get("id") is not None
                and assignee_id is None
            ):
                raise ValueError(
                    "Не найден исполнитель для задачи "
                    f"{item['id']}"
                )

            if issue is None:
                issue = RedmineIssue(
                    connection_id=connection_id,
                    project_id=project.id,
                    external_issue_id=item["id"],
                    assignee_id=assignee_id,
                    status_id=status_id,
                    subject=item["subject"],
                    description=item.get(
                        "description"
                    ),
                    priority_name=(
                        item.get("priority") or {}
                    ).get("name"),
                    tracker_name=(
                        item.get("tracker") or {}
                    ).get("name"),
                    estimated_hours=parse_decimal(
                        item.get("estimated_hours")
                    ),
                    spent_hours=parse_decimal(
                        item.get("spent_hours")
                    ),
                    done_ratio=item.get(
                        "done_ratio",
                        0,
                    ),
                    start_date=parse_date(item.get("start_date")),
                    due_date=parse_date(item.get("due_date")),
                    created_at=parse_datetime(
                        item.get("created_on")
                    ),
                    updated_at=parse_datetime(
                        item.get("updated_on")
                    ),
                    closed_at=parse_datetime(
                        item.get("closed_on")
                    ),
                )

                db.add(issue)

            else:
                issue.project_id = project.id
                issue.assignee_id = assignee_id
                issue.status_id = status_id
                issue.subject = item["subject"]

                issue.description = item.get(
                    "description"
                )

                issue.priority_name = (
                    item.get("priority") or {}
                ).get("name")

                issue.tracker_name = (
                    item.get("tracker") or {}
                ).get("name")

                issue.estimated_hours = parse_decimal(
                    item.get("estimated_hours")
                )

                issue.spent_hours = parse_decimal(
                    item.get("spent_hours")
                )

                issue.done_ratio = item.get(
                    "done_ratio",
                    0,
                )
                issue.start_date = parse_date(item.get("start_date"))
                issue.due_date = parse_date(item.get("due_date"))

                issue.created_at = parse_datetime(
                    item.get("created_on")
                )

                issue.updated_at = parse_datetime(
                    item.get("updated_on")
                )

                issue.closed_at = parse_datetime(
                    item.get("closed_on")
                )

            changed = has_changes(issue)
            db.flush()
            issue_map[item["id"]] = issue.id
            if changed:
                add_outbox(db, connection, "redmine.issue.upserted", {
                    "id": item["id"],
                    "project_id": external_project_id,
                    "assignee_external_id": assignee_data.get("id"),
                    "status_external_id": status_data.get("id"),
                    "status_name": status_details[status_data["id"]]["name"],
                    "status_is_closed": bool(status_details[status_data["id"]].get("is_closed", False)),
                    "start_date": issue.start_date.isoformat() if issue.start_date else None,
                    "due_date": issue.due_date.isoformat() if issue.due_date else None,
                    "subject": issue.subject,
                    "description": issue.description,
                    "priority_name": issue.priority_name,
                    "tracker_name": issue.tracker_name,
                    "estimated_hours": str(issue.estimated_hours) if issue.estimated_hours is not None else None,
                    "spent_hours": str(issue.spent_hours) if issue.spent_hours is not None else None,
                    "done_ratio": issue.done_ratio,
                    "created_at": issue.created_at.isoformat() if issue.created_at else None,
                    "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
                    "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
                })

        # 7. Сохраняем трудозатраты.
        for item in entries:
            entry = db.scalar(
                select(RedmineTimeEntry).where(
                    RedmineTimeEntry.connection_id
                    == connection_id,
                    RedmineTimeEntry.external_entry_id
                    == item["id"],
                )
            )

            external_issue_id = (
                item.get("issue") or {}
            ).get("id")

            external_user_id = (
                item.get("user") or {}
            ).get("id")

            issue_id = issue_map.get(
                external_issue_id
            )

            user_id = user_map.get(
                external_user_id
            )

            if user_id is None:
                raise ValueError(
                    "Не найден пользователь для "
                    f"записи времени {item['id']}"
                )

            if (
                external_issue_id is not None
                and issue_id is None
            ):
                raise ValueError(
                    "Не найдена задача для "
                    f"записи времени {item['id']}"
                )

            hours = parse_decimal(
                item.get("hours")
            )

            activity_name = (
                item.get("activity") or {}
            ).get("name")

            spent_on = date.fromisoformat(
                item["spent_on"]
            )

            if entry is None:
                entry = RedmineTimeEntry(
                    connection_id=connection_id,
                    project_id=project.id,
                    issue_id=issue_id,
                    user_id=user_id,
                    external_entry_id=item["id"],
                    hours=hours,
                    activity_name=activity_name,
                    comments=item.get("comments"),
                    spent_on=spent_on,
                )

                db.add(entry)

            else:
                entry.project_id = project.id
                entry.issue_id = issue_id
                entry.user_id = user_id
                entry.hours = hours
                entry.activity_name = activity_name
                entry.comments = item.get(
                    "comments"
                )
                entry.spent_on = spent_on

            if has_changes(entry):
                add_outbox(db, connection, "redmine.time_entry.upserted", {
                    "id": item["id"],
                    "project_id": external_project_id,
                    "issue_external_id": external_issue_id,
                    "user_external_id": external_user_id,
                    "hours": str(hours) if hours is not None else None,
                    "activity_name": activity_name,
                    "comments": entry.comments,
                    "spent_on": spent_on.isoformat(),
                })

        # 8. Сохраняем все изменения одной транзакцией.
        db.commit()

        return {
            "projects": 1,
            "users": len(users),
            "statuses": len(statuses),
            "issues": len(issues),
            "time_entries": len(entries),
        }