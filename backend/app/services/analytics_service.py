"""Analytics Service — computes engagement, RFM, categories affinity, and dashboard stats."""

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.email_campaign import EmailCampaign
from app.models.email_log import EmailLog
from app.models.event import Event
from app.models.product import Product
from app.models.user import User
from app.models.user_profile import UserProfile


class AnalyticsService:
    """Computes analytical metrics for users and platform KPIs."""

    async def compute_engagement_score(
        self, session: AsyncSession, user_id: uuid.UUID, total_spend: float, events: list[Event]
    ) -> float:
        """Computes engagement score (0-100) using the formula in CONTEXT.md section 5.

        score = (recency_score * 0.35) + (frequency_score * 0.35) + (monetary_score * 0.30)
        """
        if not events:
            return 0.0

        # 1. Recency Score
        # Find latest active timestamp
        last_active = events[0].timestamp  # events sorted desc
        days_since_last_active = (datetime.now(UTC) - last_active).days
        days_since_last_active = max(0, days_since_last_active)
        recency_score = max(0.0, 100.0 - days_since_last_active * 2)

        # 2. Frequency Score
        # Total events in last 30 days
        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
        events_30d = [e for e in events if e.timestamp >= thirty_days_ago]
        frequency_score = min(100.0, len(events_30d) * 3)

        # 3. Monetary Score
        monetary_score = min(100.0, total_spend / 10.0)

        # Total Weighted Score
        score = (recency_score * 0.35) + (frequency_score * 0.35) + (monetary_score * 0.30)
        return round(float(score), 2)

    async def build_user_profile(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> UserProfile:
        """Calculates and persists/materializes a user's analytical profile."""
        # Query all events for the user, with product details
        stmt = (
            select(Event)
            .where(Event.user_id == user_id)
            .options(selectinload(Event.product))
            .order_by(Event.timestamp.desc())
        )
        result = await session.execute(stmt)
        events = list(result.scalars().all())

        total_events = len(events)

        # Purchases and Spend
        purchase_events = [e for e in events if e.event_type == "purchase"]
        total_purchases = len(purchase_events)
        total_spend = sum(
            float(e.product.price)
            for e in purchase_events
            if e.product is not None
        )

        last_active_at = events[0].timestamp if events else None

        # Days since last purchase
        days_since_last_purchase = None
        if purchase_events:
            last_purchase_time = purchase_events[0].timestamp
            days_since_last_purchase = max(0, (datetime.now(UTC) - last_purchase_time).days)

        # RFM values
        rfm_recency = days_since_last_purchase
        rfm_frequency = total_purchases
        rfm_monetary = total_spend

        # Preferred categories (ordered by frequency)
        categories = []
        for e in events:
            cat = e.category or (e.product.category if e.product else None)
            if cat:
                categories.append(cat)
        category_counts = Counter(categories)
        preferred_categories = [cat for cat, _ in category_counts.most_common()]

        # Top 10 viewed products
        view_events = [
            e for e in events
            if e.event_type == "product_view" and e.product_id is not None
        ]
        product_counts = Counter(e.product_id for e in view_events)
        top_viewed_products = [
            prod_id for prod_id, _ in product_counts.most_common(10)
        ]

        # Engagement score
        engagement_score = await self.compute_engagement_score(
            session=session,
            user_id=user_id,
            total_spend=total_spend,
            events=events,
        )

        # Find or create UserProfile
        profile_stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        profile_res = await session.execute(profile_stmt)
        profile = profile_res.scalar_one_or_none()

        if not profile:
            profile = UserProfile(user_id=user_id)
            session.add(profile)

        profile.total_events = total_events
        profile.total_purchases = total_purchases
        profile.total_spend = total_spend
        profile.last_active_at = last_active_at
        profile.days_since_last_purchase = days_since_last_purchase
        profile.preferred_categories = preferred_categories
        profile.top_viewed_products = top_viewed_products
        profile.engagement_score = engagement_score
        profile.rfm_recency = rfm_recency
        profile.rfm_frequency = rfm_frequency
        profile.rfm_monetary = rfm_monetary
        profile.updated_at = datetime.now(UTC)

        await session.flush()
        return profile

    async def get_rolling_event_counts(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> dict:
        """Computes rolling 7-day and 30-day event counts for feature engineering."""
        now = datetime.now(UTC)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        # Fetch events for the user in the last 30 days
        stmt = select(Event).where(
            Event.user_id == user_id,
            Event.timestamp >= thirty_days_ago,
        )
        res = await session.execute(stmt)
        events_30d = list(res.scalars().all())

        total_events_30d = len(events_30d)
        total_events_7d = len(
            [e for e in events_30d if e.timestamp >= seven_days_ago]
        )
        cart_add_count_30d = len(
            [e for e in events_30d if e.event_type == "cart_add"]
        )
        purchase_count_30d = len(
            [e for e in events_30d if e.event_type == "purchase"]
        )

        return {
            "total_events_7d": total_events_7d,
            "total_events_30d": total_events_30d,
            "cart_add_count_30d": cart_add_count_30d,
            "purchase_count_30d": purchase_count_30d,
        }

    async def get_summary_stats(self, session: AsyncSession) -> dict:
        """Computes aggregate KPIs across all users for the dashboard."""
        total_users = (
            await session.execute(select(func.count(User.id)))
        ).scalar() or 0
        total_products = (
            await session.execute(select(func.count(Product.id)))
        ).scalar() or 0
        total_events = (
            await session.execute(select(func.count(Event.id)))
        ).scalar() or 0
        total_campaigns = (
            await session.execute(select(func.count(EmailCampaign.id)))
        ).scalar() or 0

        # Email Log stats
        email_stats = await session.execute(
            select(EmailLog.status, func.count(EmailLog.id)).group_by(
                EmailLog.status
            )
        )
        email_stats_dict = dict(email_stats.all())

        sent_count = email_stats_dict.get("sent", 0)
        opened_count = email_stats_dict.get("opened", 0)
        clicked_count = email_stats_dict.get("clicked", 0)
        failed_count = email_stats_dict.get("failed", 0)
        bounced_count = email_stats_dict.get("bounced", 0)
        total_emails = sum(email_stats_dict.values())

        # Average engagement score
        avg_engagement = (
            await session.execute(select(func.avg(UserProfile.engagement_score)))
        ).scalar() or 0.0

        # Conversion rate
        purchasing_users = (
            await session.execute(
                select(func.count(func.distinct(Event.user_id))).where(
                    Event.event_type == "purchase"
                )
            )
        ).scalar() or 0
        conversion_rate = (
            (purchasing_users / total_users) if total_users > 0 else 0.0
        )

        # Open and click rates
        open_rate = (
            ((opened_count + clicked_count) / total_emails * 100.0)
            if total_emails > 0
            else 0.0
        )
        click_rate = (
            (clicked_count / total_emails * 100.0) if total_emails > 0 else 0.0
        )

        return {
            "total_users": total_users,
            "total_products": total_products,
            "total_events": total_events,
            "total_campaigns": total_campaigns,
            "emails_sent": sent_count,
            "emails_opened": opened_count,
            "emails_clicked": clicked_count,
            "emails_failed": failed_count,
            "emails_bounced": bounced_count,
            "total_emails": total_emails,
            "avg_engagement_score": round(float(avg_engagement), 2),
            "conversion_rate": round(float(conversion_rate), 4),
            "open_rate": round(float(open_rate), 2),
            "click_rate": round(float(click_rate), 2),
        }
