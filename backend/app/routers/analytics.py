"""Analytics router — implements Section 4 of CONTEXT.md."""

import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date as SADate
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import check_rate_limit, get_db, verify_api_key
from app.models.event import Event
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get(
    "/summary",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
):
    """Retrieves aggregate KPI summary metrics across all users."""
    analytics_service = AnalyticsService()
    summary = await analytics_service.get_summary_stats(db)
    return summary


@router.get(
    "/events",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def get_event_time_series(
    days: int = Query(30, ge=1, le=90),
    event_type: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves daily event counts (time-series) for dashboard charts."""
    start_date = datetime.now(UTC) - timedelta(days=days)

    stmt = (
        select(
            cast(Event.timestamp, SADate).label("date"),
            func.count(Event.id).label("count"),
        )
        .where(Event.timestamp >= start_date)
        .group_by(cast(Event.timestamp, SADate))
        .order_by(cast(Event.timestamp, SADate).asc())
    )

    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if user_id:
        stmt = stmt.where(Event.user_id == user_id)

    result = await db.execute(stmt)
    rows = result.all()

    # Format result as a list of dicts: [{"date": "2026-05-22", "count": 10}, ...]
    time_series = []
    for date_val, count_val in rows:
        time_series.append(
            {
                "date": date_val.isoformat() if isinstance(date_val, date) else str(date_val),
                "count": count_val,
            }
        )

    return time_series
