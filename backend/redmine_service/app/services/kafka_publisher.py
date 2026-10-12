
import asyncio
import json
import os
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer
from sqlalchemy import select

from redmine_service.app.database import SessionLocal
from redmine_service.app.models import RedmineOutboxEvent


TOPICS = {
    "redmine.issue.upserted": "redmine.issues",
    "redmine.time_entry.upserted": "redmine.time_entries",
}


async def publish_pending_events():
    servers = os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS",
        "localhost:9092",
    )

    producer = AIOKafkaProducer(
        bootstrap_servers=servers,
        acks="all",
        value_serializer=lambda value: json.dumps(
            value,
            ensure_ascii=False,
        ).encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8"),
    )

    published = 0

    await producer.start()

    try:
        with SessionLocal() as db:
            events = db.scalars(
                select(RedmineOutboxEvent)
                .where(
                    RedmineOutboxEvent.published_at.is_(None)
                )
                .order_by(RedmineOutboxEvent.created_at)
                .with_for_update(skip_locked=True)
            ).all()

            for event in events:
                topic = TOPICS.get(event.event_type)

                if topic is None:
                    print(
                        "Неизвестный тип события:",
                        event.event_type,
                    )
                    continue

                payload = dict(event.payload)
                payload["event_id"] = str(event.id)

                connection_id = str(event.connection_id)
                external_id = str(
                    payload.get("data", {}).get("id", "")
                )

                key = f"{connection_id}:{external_id}"

                try:
                    await producer.send_and_wait(
                        topic,
                        key=key,
                        value=payload,
                    )

                    event.published_at = datetime.now(
                        timezone.utc
                    )

                    db.commit()

                    published += 1

                    print(
                        f"Отправлено: {event.event_type} "
                        f"| ID: {external_id}"
                    )

                except Exception:
                    db.rollback()
                    raise

    finally:
        await producer.stop()

    return published


if __name__ == "__main__":
    count = asyncio.run(publish_pending_events())
    print("Опубликовано событий:", count)
