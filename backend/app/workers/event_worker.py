"""Event background worker — consumes from Redis Stream and persists to PostgreSQL."""

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.event import Event

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("event_worker")


async def dead_letter_message(redis_client: aioredis.Redis, msg_id: str, payload_str: str, error_msg: str) -> None:
    """Pushes a failed message to the dead-letter stream ``events:failed``."""
    try:
        await redis_client.xadd(
            "events:failed",
            {
                "original_id": msg_id,
                "payload": payload_str,
                "error": error_msg,
                "failed_at": datetime.now(UTC).isoformat(),
            },
        )
        logger.warning("Dead-lettered message %s due to error: %s", msg_id, error_msg)
    except Exception as e:
        logger.error("Failed to dead-letter message %s: %s", msg_id, e)


async def process_event_payload(session: AsyncSession, data: dict) -> Event:
    """Parses and constructs an Event ORM model from a stream message payload."""
    metadata_val = data.get("metadata", {})
    if isinstance(metadata_val, str):
        try:
            metadata_val = json.loads(metadata_val)
        except json.JSONDecodeError:
            metadata_val = {}

    timestamp_val = data.get("timestamp")
    if timestamp_val:
        try:
            timestamp = datetime.fromisoformat(timestamp_val)
        except ValueError:
            timestamp = datetime.now(UTC)
    else:
        timestamp = datetime.now(UTC)

    event = Event(
        id=uuid.UUID(data["id"]) if data.get("id") else uuid.uuid4(),
        user_id=uuid.UUID(data["user_id"]),
        event_type=data["event_type"],
        product_id=uuid.UUID(data["product_id"]) if data.get("product_id") else None,
        session_id=data.get("session_id"),
        category=data.get("category"),
        metadata_=metadata_val,
        timestamp=timestamp,
    )
    return event


async def process_batch(redis_client: aioredis.Redis, batch: list[tuple[str, str]]) -> None:
    """Attempts to insert a batch of messages. Falls back to one-by-one if error occurs."""
    # Parsed events list and mapping back to message IDs
    parsed_events = []
    msg_map = []  # list of (msg_id, payload_str, parsed_event_or_error)

    for msg_id, payload_str in batch:
        try:
            data = json.loads(payload_str)
            event = await process_event_payload(None, data)
            parsed_events.append(event)
            msg_map.append((msg_id, payload_str, event))
        except Exception as e:
            # Structurally invalid event — dead-letter it immediately
            err_msg = f"Validation/JSON error: {e}"
            await dead_letter_message(redis_client, msg_id, payload_str, err_msg)
            await redis_client.xack("events:raw", "event_workers", msg_id)
            msg_map.append((msg_id, payload_str, e))

    if not parsed_events:
        return

    # Try bulk insertion
    async with async_session_factory() as session:
        try:
            session.add_all(parsed_events)
            await session.commit()

            # Acknowledge all successful message IDs
            success_ids = [m[0] for m in msg_map if not isinstance(m[2], Exception)]
            if success_ids:
                await redis_client.xack("events:raw", "event_workers", *success_ids)
                logger.info("Successfully bulk persisted %d events", len(success_ids))
            return
        except SQLAlchemyError as se:
            await session.rollback()
            logger.warning("Bulk insert failed due to database error: %s. Falling back to sequential.", se)

    # Fallback to sequential insertion to isolate the error
    for msg_id, payload_str, item in msg_map:
        if isinstance(item, Exception):
            continue  # Already handled above

        async with async_session_factory() as session:
            try:
                session.add(item)
                await session.commit()
                await redis_client.xack("events:raw", "event_workers", msg_id)
            except Exception as e:
                await session.rollback()
                err_msg = f"Database insertion error: {e}"
                await dead_letter_message(redis_client, msg_id, payload_str, err_msg)
                await redis_client.xack("events:raw", "event_workers", msg_id)


async def start_event_worker(redis_client: aioredis.Redis) -> None:
    """Subscribes to events:raw and continuously processes incoming event streams."""
    group_name = "event_workers"
    stream_name = "events:raw"
    consumer_name = f"worker_{uuid.uuid4().hex[:6]}"

    # Setup Consumer Group
    try:
        await redis_client.xgroup_create(stream_name, group_name, id="0", mkstream=True)
        logger.info("Created Redis stream group %s for %s", group_name, stream_name)
    except Exception as e:
        if "BUSYGROUP" in str(e):
            logger.info("Redis stream group %s already exists", group_name)
        else:
            logger.error("Error creating Redis group: %s", e)

    logger.info("Event worker %s started listening to Redis stream...", consumer_name)

    while True:
        try:
            # 1. Read pending messages (delivered but not acknowledged)
            messages = await redis_client.xreadgroup(
                group_name, consumer_name, {stream_name: "0"}, count=50
            )

            # 2. If no pending messages, read new messages (block for up to 1 second)
            if not messages or not messages[0][1]:
                messages = await redis_client.xreadgroup(
                    group_name, consumer_name, {stream_name: ">"}, count=50, block=1000
                )

            if not messages:
                await asyncio.sleep(0.1)
                continue

            # Process batch
            batch = []
            for stream, stream_messages in messages:
                for msg_id, data in stream_messages:
                    payload_str = data.get("payload", "{}")
                    batch.append((msg_id, payload_str))

            if batch:
                await process_batch(redis_client, batch)

        except asyncio.CancelledError:
            logger.info("Event worker Cancelled. Exiting...")
            break
        except Exception as e:
            logger.error("Error in event worker loop: %s", e)
            await asyncio.sleep(1.0)
