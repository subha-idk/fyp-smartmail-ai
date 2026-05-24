"""Feature Pipeline — Queries PostgreSQL and constructs the user-level features for training."""

import asyncio
import os
from datetime import UTC, datetime, timedelta
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.event import Event
from app.services.analytics_service import AnalyticsService


def check_intent_conversion(user_events: list[Event]) -> int:
    """Assigns converted = 1 if a purchase event occurs within 7 days after a product_view event."""
    sorted_events = sorted(user_events, key=lambda e: e.timestamp)
    views = [e for e in sorted_events if e.event_type == "product_view"]
    purchases = [e for e in sorted_events if e.event_type == "purchase"]

    for v in views:
        for p in purchases:
            if p.timestamp >= v.timestamp and p.timestamp <= v.timestamp + timedelta(days=7):
                return 1
    return 0


async def get_features_df(session: AsyncSession) -> pd.DataFrame:
    """Builds and returns the features DataFrame for all users.

    Ensures profiles are materialized before returning.
    """
    # 1. Rebuild profiles to ensure database is fresh
    user_stmt = select(User.id)
    res = await session.execute(user_stmt)
    user_ids = res.scalars().all()

    analytics_service = AnalyticsService()
    for uid in user_ids:
        await analytics_service.build_user_profile(session, uid)
    await session.commit()

    # 2. Query all profiles and events
    profile_stmt = select(UserProfile)
    res = await session.execute(profile_stmt)
    profiles = res.scalars().all()

    event_stmt = select(Event)
    res = await session.execute(event_stmt)
    events = res.scalars().all()

    # Group events by user_id
    user_events_map = {}
    for e in events:
        user_events_map.setdefault(e.user_id, []).append(e)

    now = datetime.now(UTC)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    rows = []
    for p in profiles:
        user_events = user_events_map.get(p.user_id, [])

        # Calculate active time
        last_active = p.last_active_at or (user_events[0].timestamp if user_events else None)
        days_since_last_active = (now - last_active).days if last_active else 365
        days_since_last_active = max(0, days_since_last_active)

        # Churn Label
        churned = 1 if days_since_last_active > 60 else 0

        # Intent Label
        converted = check_intent_conversion(user_events)

        # Rolling event counts
        events_7d = [e for e in user_events if e.timestamp >= seven_days_ago]
        events_30d = [e for e in user_events if e.timestamp >= thirty_days_ago]
        cart_adds_30d = [e for e in events_30d if e.event_type == "cart_add"]
        purchases_30d = [e for e in events_30d if e.event_type == "purchase"]

        # Default recency to 365 if no purchases
        days_since_last_purchase = p.days_since_last_purchase if p.days_since_last_purchase is not None else 365
        rfm_recency = p.rfm_recency if p.rfm_recency is not None else 365

        rows.append({
            "user_id": str(p.user_id),
            "days_since_last_active": days_since_last_active,
            "days_since_last_purchase": days_since_last_purchase,
            "total_events_7d": len(events_7d),
            "total_events_30d": len(events_30d),
            "total_purchases": p.total_purchases,
            "total_spend": float(p.total_spend or 0.0),
            "cart_add_count_30d": len(cart_adds_30d),
            "purchase_count_30d": len(purchases_30d),
            "engagement_score": float(p.engagement_score or 0.0),
            "rfm_recency": rfm_recency,
            "rfm_frequency": p.rfm_frequency or 0,
            "rfm_monetary": float(p.rfm_monetary or 0.0),
            "churned": churned,
            "converted": converted,
        })

    return pd.DataFrame(rows)


async def main():
    print("Initializing feature extraction...")
    async with async_session_factory() as session:
        df = await get_features_df(session)

    if df.empty:
        print("No users found to build features.")
        return

    # Base path relative to this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    churn_path = os.path.join(base_dir, "churn_features.csv")
    intent_path = os.path.join(base_dir, "intent_features.csv")

    # Save features
    df.to_csv(churn_path, index=False)
    print(f"Saved Churn features ({len(df)} rows) to: {churn_path}")

    df.to_csv(intent_path, index=False)
    print(f"Saved Intent features ({len(df)} rows) to: {intent_path}")


if __name__ == "__main__":
    asyncio.run(main())
