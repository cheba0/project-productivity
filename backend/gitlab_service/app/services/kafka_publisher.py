
import asyncio
import json
import os
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer
from sqlalchemy import select

from gitlab_service.app.database import SessionLocal
from gitlab_service.app.models import GitLabOutboxEvent


async def publish_pending_events():
    producer = AIOKafkaProducer(
        bootstrap_servers=os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "localhost:9092",
        ),
    )

    await producer.start()

    published = 0

    try:
        with SessionLocal() as db:
            events = db.scalars(
                select(GitLabOutboxEvent)
                .where(GitLabOutboxEvent.published_at.is_(None))
                .order_by(GitLabOutboxEvent.created_at)
            ).all()

            for event in events:
                await producer.send_and_wait(
                    event.topic,
                    value=event.payload.encode("utf-8"),
                    key=event.event_key.encode("utf-8"),
                )

                event.published_at = datetime.now(timezone.utc)
                db.commit()
                published += 1

    finally:
        await producer.stop()

    return published


if __name__ == "__main__":
    count = asyncio.run(publish_pending_events())
    print("Опубликовано событий:", count)
