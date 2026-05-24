"""Tests for Phase 3: User Profile and Analytics Engine."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db, get_redis
from app.main import app
from app.models.email_log import EmailLog
from app.models.event import Event
from app.models.user_profile import UserProfile
from app.services.analytics_service import AnalyticsService
from tests.test_track import MockRedis


@pytest.fixture
async def client(test_session: AsyncSession) -> AsyncClient:
    """Provides an AsyncClient pointing to the FastAPI app with overridden dependencies."""
    app.dependency_overrides[get_db] = lambda: test_session
    app.dependency_overrides[get_redis] = lambda: MockRedis()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestAnalyticsService:
    """Tests metrics calculations, profile building, and rolling counts inside AnalyticsService."""

    async def test_build_user_profile(
        self, test_session: AsyncSession, seed_users, seed_products
    ):
        """Rebuilds a user profile and asserts all metrics, category affinity, and RFM scores."""
        user = seed_users[0]
        # Seed custom events to verify calculations
        # Product 1 ($10) -> view (2 days ago), purchase (1 day ago)
        # Product 2 ($20) -> view (3 days ago), purchase (3 days ago), view (1 hour ago)
        now = datetime.now(UTC)
        events = [
            Event(
                user_id=user.id,
                event_type="product_view",
                product_id=seed_products[1].id,
                timestamp=now - timedelta(hours=1),
                category="fashion",
            ),
            Event(
                user_id=user.id,
                event_type="purchase",
                product_id=seed_products[0].id,
                timestamp=now - timedelta(days=1),
                category="electronics",
            ),
            Event(
                user_id=user.id,
                event_type="product_view",
                product_id=seed_products[0].id,
                timestamp=now - timedelta(days=2),
                category="electronics",
            ),
            Event(
                user_id=user.id,
                event_type="purchase",
                product_id=seed_products[1].id,
                timestamp=now - timedelta(days=3),
                category="fashion",
            ),
            Event(
                user_id=user.id,
                event_type="product_view",
                product_id=seed_products[1].id,
                timestamp=now - timedelta(days=3),
                category="fashion",
            ),
        ]
        test_session.add_all(events)
        await test_session.commit()

        service = AnalyticsService()
        profile = await service.build_user_profile(test_session, user.id)

        # Assert totals
        assert profile.total_events == 5
        assert profile.total_purchases == 2
        # Spend: Product 1 ($10) + Product 2 ($20) = $30
        assert float(profile.total_spend) == 30.0

        # Last active & purchase recency
        assert profile.last_active_at is not None
        assert profile.days_since_last_purchase == 1  # latest purchase was 1 day ago

        # Preferred categories: fashion (3 events) and electronics (2 events)
        assert profile.preferred_categories == ["fashion", "electronics"]

        # Top viewed products
        # Product 2 viewed twice, Product 1 viewed once
        assert profile.top_viewed_products == [seed_products[1].id, seed_products[0].id]

        # RFM values
        assert profile.rfm_recency == 1
        assert profile.rfm_frequency == 2
        assert float(profile.rfm_monetary) == 30.0

        # Engagement score calculation check
        # recency_score = max(0, 100 - days_since_last_active * 2) = max(0, 100 - 0 * 2) = 100
        # frequency_score = min(100, events_30d * 3) = min(100, 5 * 3) = 15
        # monetary_score = min(100, spend / 10) = min(100, 30 / 10) = 3
        # score = 100 * 0.35 + 15 * 0.35 + 3 * 0.30 = 35 + 5.25 + 0.9 = 41.15
        assert float(profile.engagement_score) == 41.15

    async def test_get_rolling_event_counts(
        self, test_session: AsyncSession, seed_users, seed_products
    ):
        """Asserts rolling 7-day and 30-day event count metrics are correctly computed."""
        user = seed_users[1]
        now = datetime.now(UTC)
        events = [
            Event(
                user_id=user.id,
                event_type="product_view",
                timestamp=now - timedelta(days=2),
            ),
            Event(
                user_id=user.id,
                event_type="cart_add",
                timestamp=now - timedelta(days=5),
            ),
            Event(
                user_id=user.id,
                event_type="purchase",
                timestamp=now - timedelta(days=10),
            ),
        ]
        test_session.add_all(events)
        await test_session.commit()

        service = AnalyticsService()
        counts = await service.get_rolling_event_counts(test_session, user.id)

        assert counts["total_events_7d"] == 2  # view + cart_add
        assert counts["total_events_30d"] == 3  # view + cart_add + purchase
        assert counts["cart_add_count_30d"] == 1
        assert counts["purchase_count_30d"] == 1


@pytest.mark.asyncio
class TestAnalyticsAPIEndpoints:
    """Tests the dashboard and user analytical profile REST endpoints."""

    async def test_get_user_profile_endpoint(self, client: AsyncClient, seed_users):
        """Retrieves user profile and tests lazy/on-the-fly building."""
        user_id = seed_users[0].id
        res = await client.get(
            f"/api/users/{user_id}/profile",
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["user_id"] == str(user_id)
        assert "engagement_score" in data
        assert "rfm_monetary" in data

    async def test_list_users_endpoint(self, client: AsyncClient, seed_users):
        """Lists users with pagination."""
        res = await client.get(
            "/api/users?page=1&limit=2",
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["users"]) == 2
        assert data["total"] == len(seed_users)
        assert data["page"] == 1
        assert data["limit"] == 2

    async def test_get_summary_stats_endpoint(
        self, client: AsyncClient, test_session: AsyncSession, seed_users
    ):
        """Computes summary stats and asserts conversion rates and open/click rates."""
        # Setup email logs and purchase event to verify metrics
        log = EmailLog(
            user_id=seed_users[0].id,
            email_type="retention",
            status="opened",
        )
        purchase = Event(
            user_id=seed_users[0].id,
            event_type="purchase",
        )
        test_session.add_all([log, purchase])
        await test_session.commit()

        # Build profiles so averages work
        service = AnalyticsService()
        for u in seed_users:
            await service.build_user_profile(test_session, u.id)
        await test_session.commit()

        res = await client.get(
            "/api/analytics/summary",
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_users"] == len(seed_users)
        assert data["total_emails"] == 1
        assert data["emails_opened"] == 1
        assert data["open_rate"] == 100.0  # 1 opened / 1 total * 100

    async def test_get_event_time_series_endpoint(
        self, client: AsyncClient, test_session: AsyncSession, seed_users
    ):
        """Retrieves daily grouped event counts for dashboard charting."""
        user = seed_users[0]
        # Seed 2 events on same day, 1 event on previous day
        now = datetime.now(UTC)
        events = [
            Event(user_id=user.id, event_type="search", timestamp=now),
            Event(user_id=user.id, event_type="product_view", timestamp=now),
            Event(
                user_id=user.id,
                event_type="product_view",
                timestamp=now - timedelta(days=1),
            ),
        ]
        test_session.add_all(events)
        await test_session.commit()

        res = await client.get(
            "/api/analytics/events?days=5",
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1  # Should have dates
        # Assert structure
        assert "date" in data[0]
        assert "count" in data[0]
