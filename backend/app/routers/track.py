"""Event tracking router — implements Section 4 and 9 of CONTEXT.md."""

import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import check_rate_limit, get_db, get_redis, verify_api_key
from app.models.email_log import EmailLog
from app.schemas.event import EventPayload

router = APIRouter(prefix="/api/track", tags=["Tracking"])

# 1x1 transparent GIF pixel bytes
TRANSPARENT_GIF = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff"
    b"\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
)


async def enqueue_event(redis_client, event_id: uuid.UUID, payload: EventPayload) -> None:
    """Serializes event details and enqueues to the Redis Stream ``events:raw``."""
    data = {
        "id": str(event_id),
        "user_id": str(payload.user_id),
        "event_type": payload.event_type,
        "product_id": str(payload.product_id) if payload.product_id else None,
        "session_id": payload.session_id,
        "category": payload.category,
        "metadata": json.dumps(payload.metadata),
        "timestamp": payload.timestamp.isoformat(),
    }
    # Store key/value of payload as JSON string in stream fields
    await redis_client.xadd("events:raw", {"payload": json.dumps(data)})


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def track_event(
    payload: EventPayload,
    redis=Depends(get_redis),
):
    """Ingests a single event and pushes it to the event stream."""
    event_id = uuid.uuid4()
    try:
        await enqueue_event(redis, event_id, payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue event: {e}",
        )
    return {"status": "queued", "event_id": str(event_id)}


@router.post(
    "/batch",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def track_events_batch(
    payloads: list[EventPayload],
    redis=Depends(get_redis),
):
    """Ingests a batch of events (maximum 100) and pushes them to the event stream."""
    if len(payloads) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size exceeds maximum limit of 100 events.",
        )

    queued = 0
    failed = 0

    async with redis.pipeline() as pipe:
        for payload in payloads:
            event_id = uuid.uuid4()
            data = {
                "id": str(event_id),
                "user_id": str(payload.user_id),
                "event_type": payload.event_type,
                "product_id": str(payload.product_id) if payload.product_id else None,
                "session_id": payload.session_id,
                "category": payload.category,
                "metadata": json.dumps(payload.metadata),
                "timestamp": payload.timestamp.isoformat(),
            }
            try:
                await pipe.xadd("events:raw", {"payload": json.dumps(data)})
                queued += 1
            except Exception:
                failed += 1

        if queued > 0:
            await pipe.execute()

    return {"queued": queued, "failed": failed}


@router.get("/open/{token}")
async def track_email_open(
    token: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Tracks email open (public tracking pixel) and enqueues email_open event."""
    # Find matching email log
    stmt = select(EmailLog).where(EmailLog.open_token == token)
    result = await db.execute(stmt)
    email_log = result.scalar_one_or_none()

    if not email_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email log not found",
        )

    # Enforce idempotence: if already opened, return pixel immediately
    if email_log.opened_at is not None:
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
        return Response(content=TRANSPARENT_GIF, media_type="image/gif", headers=headers)

    now = datetime.now(UTC)
    email_log.status = "opened"
    email_log.opened_at = now

    # Enqueue event to stream
    payload = EventPayload(
        user_id=email_log.user_id,
        event_type="email_open",
        metadata={
            "email_log_id": str(email_log.id),
            "campaign_id": str(email_log.campaign_id) if email_log.campaign_id else None,
        },
        timestamp=now,
    )
    await enqueue_event(redis, uuid.uuid4(), payload)
    await db.commit()

    # Always return transparent 1x1 pixel image
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return Response(content=TRANSPARENT_GIF, media_type="image/gif", headers=headers)


@router.get("/click/{token}")
async def track_email_click(
    token: str,
    redirect: str = Query(default="", alias="redirect"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Tracks email click, updates email log, enqueues email_click event, and redirects."""
    # Find matching email log
    stmt = select(EmailLog).where(EmailLog.click_token == token)
    result = await db.execute(stmt)
    email_log = result.scalar_one_or_none()

    if not email_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email log not found",
        )

    redirect_url = redirect if redirect else settings.FRONTEND_URL

    # Enforce idempotence: if already clicked, redirect immediately
    if email_log.clicked_at is not None:
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    now = datetime.now(UTC)
    email_log.status = "clicked"
    email_log.clicked_at = now
    if not email_log.opened_at:
        email_log.opened_at = now

    # Enqueue event to stream
    payload = EventPayload(
        user_id=email_log.user_id,
        event_type="email_click",
        metadata={
            "email_log_id": str(email_log.id),
            "campaign_id": str(email_log.campaign_id) if email_log.campaign_id else None,
        },
        timestamp=now,
    )
    await enqueue_event(redis, uuid.uuid4(), payload)
    await db.commit()

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
