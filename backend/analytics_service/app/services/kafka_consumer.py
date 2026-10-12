import asyncio
import json
import os

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from aiokafka import AIOKafkaConsumer
from sqlalchemy import select

from analytics_service.app.database import SessionLocal
from analytics_service.app.models import (
    AnalyticsCommit,
    AnalyticsTask,
    AnalyticsTimeEntry,
    ProjectMapping,
)
from analytics_service.app.services.task_commit_service import (
    link_commit_to_tasks,
)


def parse_datetime(value):
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def get_project_mapping(db, event, source):
    workspace_id = UUID(event["workspace_id"])
    connection_id = UUID(event["connection_id"])

    data = event.get("data") or {}

    if source == "gitlab":
        project_id = int(event["project_id"])

        return db.scalar(
            select(ProjectMapping).where(
                ProjectMapping.workspace_id == workspace_id,
                ProjectMapping.gitlab_connection_id == connection_id,
                ProjectMapping.gitlab_project_id == project_id,
            )
        )

    if source == "redmine":
        project_id = int(data["project_id"])

        return db.scalar(
            select(ProjectMapping).where(
                ProjectMapping.workspace_id == workspace_id,
                ProjectMapping.redmine_connection_id == connection_id,
                ProjectMapping.redmine_project_id == project_id,
            )
        )

    raise ValueError("Unknown source")


# ==========================================
# GITLAB COMMITS
# ==========================================

def save_commit_event(event):
    if event.get("event_type") != "gitlab.commit.created":
        return "skipped"

    data = event.get("data") or {}

    required = (
        "workspace_id",
        "connection_id",
        "project_id",
        "event_id",
    )

    if any(not event.get(field) for field in required):
        raise ValueError("Missing event metadata")

    sha = data.get("sha")

    if not sha:
        raise ValueError("Missing commit SHA")

    workspace_id = UUID(event["workspace_id"])
    connection_id = UUID(event["connection_id"])
    project_id = int(event["project_id"])

    with SessionLocal() as db:
        mapping = db.scalar(
            select(ProjectMapping).where(
                ProjectMapping.workspace_id == workspace_id,
                ProjectMapping.gitlab_connection_id == connection_id,
                ProjectMapping.gitlab_project_id == project_id,
            )
        )

        if mapping is None:
            return "unmapped"

        commit = db.scalar(
            select(AnalyticsCommit).where(
                AnalyticsCommit.project_mapping_id == mapping.id,
                AnalyticsCommit.sha == sha,
            )
        )

        created = commit is None

        if created:
            commit = AnalyticsCommit(
                project_mapping_id=mapping.id,
                sha=sha,
            )
            db.add(commit)

        # Сохраняем название коммита, если оно есть в событии
        if "title" in data:
            commit.title = data["title"]

        commit.author_name = data.get("author_name")

        # Не стираем email, если старое событие
        # пришло без этого поля.
        if data.get("author_email") is not None:
            commit.author_email = data["author_email"]

        commit.authored_at = parse_datetime(
            data.get("authored_at")
        )

        commit.additions = data.get("additions") or 0
        commit.deletions = data.get("deletions") or 0
        commit.is_merge = data.get("is_merge", False)

        linked_count = link_commit_to_tasks(
            db=db,
            project_mapping_id=mapping.id,
            commit_sha=sha,
            title=commit.title,
        )

        db.commit()

        result = "saved" if created else "updated"

        if linked_count:
            result += f", linked_tasks={linked_count}"

        return result
# ==========================================
# REDMINE ISSUES
# ==========================================

def save_issue_event(event):
    if event.get("event_type") != "redmine.issue.upserted":
        return "skipped"

    data = event.get("data") or {}

    issue_id = int(data["id"])

    with SessionLocal() as db:
        mapping = get_project_mapping(
            db, event, "redmine"
        )

        if mapping is None:
            return "unmapped"

        task = db.scalar(
            select(AnalyticsTask).where(
                AnalyticsTask.project_mapping_id == mapping.id,
                AnalyticsTask.redmine_issue_id == issue_id,
            )
        )

        created = task is None

        if created:
            task = AnalyticsTask(
                project_mapping_id=mapping.id,
                redmine_issue_id=issue_id,
            )
            db.add(task)

        task.subject = data["subject"]

        task.assignee_redmine_user_id = (
            data.get("assignee_external_id")
        )

        status_external_id = data.get(
            "status_external_id"
        )

        # Статусы из тестового Redmine:
        # 1 - Новая
        # 2 - В работе
        # 3 - На проверке
        # 4 - Закрыта
        #
        # Для текущего тестового подключения.
        status_names = {
            1: "Новая",
            2: "В работе",
            3: "На проверке",
            4: "Закрыта",
        }

        status_id = int(status_external_id)

        if status_id not in status_names:
            raise ValueError(
                f"Unknown Redmine status: {status_id}"
            )

        task.status_name = status_names[status_id]
        task.is_closed = status_id == 4

        task.estimated_hours = (
            Decimal(str(data["estimated_hours"]))
            if data.get("estimated_hours") is not None
            else None
        )

        task.spent_hours = (
            Decimal(str(data["spent_hours"]))
            if data.get("spent_hours") is not None
            else None
        )

        task.created_at = parse_datetime(
            data.get("created_at")
        )

        task.closed_at = parse_datetime(
            data.get("closed_at")
        )

        db.commit()

        return "saved" if created else "updated"


# ==========================================
# REDMINE TIME ENTRIES
# ==========================================

def save_time_entry_event(event):
    if event.get("event_type") != "redmine.time_entry.upserted":
        return "skipped"

    data = event.get("data") or {}

    entry_id = int(data["id"])

    with SessionLocal() as db:
        mapping = get_project_mapping(
            db, event, "redmine"
        )

        if mapping is None:
            return "unmapped"

        entry = db.scalar(
            select(AnalyticsTimeEntry).where(
                AnalyticsTimeEntry.project_mapping_id == mapping.id,
                AnalyticsTimeEntry.redmine_time_entry_id == entry_id,
            )
        )

        created = entry is None

        if created:
            entry = AnalyticsTimeEntry(
                project_mapping_id=mapping.id,
                redmine_time_entry_id=entry_id,
            )
            db.add(entry)

        entry.redmine_issue_id = (
            int(data["issue_external_id"])
            if data.get("issue_external_id") is not None
            else None
        )

        entry.redmine_user_id = int(
            data["user_external_id"]
        )

        entry.hours = Decimal(
            str(data["hours"])
        )

        entry.activity_name = data.get(
            "activity_name"
        )

        entry.spent_on = date.fromisoformat(
            data["spent_on"]
        )

        db.commit()

        return "saved" if created else "updated"


# ==========================================
# EVENT DISPATCHER
# ==========================================

def process_event(event):
    event_type = event.get("event_type")

    if event_type == "gitlab.commit.created":
        return save_commit_event(event)

    if event_type == "redmine.issue.upserted":
        return save_issue_event(event)

    if event_type == "redmine.time_entry.upserted":
        return save_time_entry_event(event)

    return "skipped"


# ==========================================
# KAFKA CONSUMER
# ==========================================

async def consume_events():
    consumer = AIOKafkaConsumer(
        "gitlab.commits",
        "redmine.issues",
        "redmine.time_entries",
        bootstrap_servers=os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "localhost:9092",
        ),
        group_id="analytics-events-v2",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(
            value.decode("utf-8")
        ),
    )

    await consumer.start()

    print("Analytics Consumer запущен.")
    print("Ожидание событий GitLab и Redmine...")

    try:
        async for message in consumer:
            try:
                result = await asyncio.to_thread(
                    process_event,
                    message.value,
                )

                print(
                    f"Topic: {message.topic} | "
                    f"Partition: {message.partition} | "
                    f"Offset: {message.offset} | "
                    f"Result: {result}"
                )

                if result == "unmapped":
                    print(
                        "Нет соответствия проектов. "
                        "Сообщение не подтверждено."
                    )
                    break

                # Подтверждаем только успешно
                # обработанные сообщения.
                await consumer.commit()

            except Exception as error:
                print(
                    "Ошибка обработки:",
                    type(error).__name__,
                    str(error),
                )

                print(
                    "Сообщение не подтверждено. "
                    "Consumer остановлен."
                )
                break

    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(consume_events())
