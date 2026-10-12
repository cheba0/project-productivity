
import asyncio
import json
import os
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from aiokafka import AIOKafkaConsumer
from sqlalchemy import select

from analytics_service.app.database import SessionLocal
from analytics_service.app.models import (
    AnalyticsTask,
    ProjectMapping,
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

    return Decimal(str(value))


def save_issue_event(event):
    if event.get("event_type") != "redmine.issue.upserted":
        return "skipped"

    required = (
        "event_id",
        "workspace_id",
        "connection_id",
    )

    if any(not event.get(field) for field in required):
        raise ValueError("Missing event metadata")

    data = event.get("data") or {}

    if data.get("id") is None or data.get("project_id") is None:
        raise ValueError("Missing Redmine issue or project ID")

    workspace_id = UUID(event["workspace_id"])
    connection_id = UUID(event["connection_id"])
    project_id = int(data["project_id"])
    issue_id = int(data["id"])

    with SessionLocal() as db:
        mapping = db.scalar(
            select(ProjectMapping).where(
                ProjectMapping.workspace_id == workspace_id,
                ProjectMapping.redmine_connection_id == connection_id,
                ProjectMapping.redmine_project_id == project_id,
            )
        )

        if mapping is None:
            return "unmapped"

        task = db.scalar(
            select(AnalyticsTask)
            .where(
                AnalyticsTask.project_mapping_id == mapping.id,
                AnalyticsTask.redmine_issue_id == issue_id,
            )
            .with_for_update()
        )

        if task is None:
            task = AnalyticsTask(
                project_mapping_id=mapping.id,
                redmine_issue_id=issue_id,
            )
            db.add(task)
            result = "saved"
        else:
            result = "updated"

        status_id = data.get("status_external_id")
        closed_at = parse_datetime(data.get("closed_at"))

        status_names = {
            1: "Новая",
            2: "В работе",
            3: "На проверке",
            4: "Закрыта",
        }

        if status_id is None:
            raise ValueError("Missing Redmine status ID")

        status_id = int(status_id)

        # Временное соответствие для тестового Redmine.
        # В рабочем приложении статусы должны
        # определяться отдельно для каждого подключения.
        if status_id not in status_names:
            raise ValueError(
                f"Unknown Redmine status: {status_id}"
            )

        task.subject = data.get("subject") or ""
        task.assignee_redmine_user_id = (
            data.get("assignee_external_id")
        )
        task.status_name = status_names[status_id]
        task.is_closed = (
            status_id == 4
        )
        task.estimated_hours = parse_decimal(
            data.get("estimated_hours")
        )
        task.spent_hours = parse_decimal(
            data.get("spent_hours")
        )
        task.created_at = parse_datetime(
            data.get("created_at")
        )
        task.closed_at = closed_at

        db.commit()

        return result


async def consume_redmine():
    consumer = AIOKafkaConsumer(
        "redmine.issues",
        bootstrap_servers=os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "localhost:9092",
        ),
        group_id="analytics-redmine-issues-v1",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(
            value.decode("utf-8")
        ),
    )

    await consumer.start()

    print("Redmine Consumer запущен.")
    print("Ожидание событий Redmine...")

    try:
        async for message in consumer:
            try:
                result = await asyncio.to_thread(
                    save_issue_event,
                    message.value,
                )

                print(
                    f"Partition: {message.partition} "
                    f"| Offset: {message.offset} "
                    f"| Результат: {result}"
                )

                if result == "unmapped":
                    print(
                        "Не найдено соответствие проектов. "
                        "Сообщение не подтверждено."
                    )
                    break

                await consumer.commit()

            except Exception as error:
                print(
                    "Ошибка обработки:",
                    type(error).__name__,
                    str(error),
                )
                print(
                    "Consumer остановлен. "
                    "Сообщение не подтверждено."
                )
                break

    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(consume_redmine())
