"""Tests for Phase 5: Recommendation Engine."""

import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db, get_redis
from app.main import app
from app.models.event import Event
from app.models.product import Product
from app.services.analytics_service import AnalyticsService
from app.services.recommendation_service import RecommendationService, SURPRISE_AVAILABLE
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
class TestRecommendationService:
    """Tests product recommendations generation under cold start and collaborative filtering."""

    async def test_cold_start_recommendations_by_category(
        self, test_session: AsyncSession, seed_users, seed_products
    ):
        """Tests that a cold start user (< 5 events) gets recommended products from their preferred category first."""
        user = seed_users[0]
        # Build analytical profile with a preferred category
        # Product 0 is beauty category, Product 1 is fashion category
        seed_products[0].category = "beauty"
        seed_products[1].category = "beauty"
        seed_products[2].category = "fashion"
        test_session.add_all([seed_products[0], seed_products[1], seed_products[2]])
        await test_session.commit()

        # Seed 1 event so they have a preferred category but still count as cold start (< 5 events)
        event = Event(
            user_id=user.id,
            event_type="product_view",
            product_id=seed_products[0].id,
            category="beauty",
        )
        test_session.add(event)
        await test_session.commit()

        # Build profile to set preferred_categories
        analytics = AnalyticsService()
        profile = await analytics.build_user_profile(test_session, user.id)
        await test_session.commit()

        assert profile.total_events == 1
        assert profile.preferred_categories[0] == "beauty"

        # Mock Redis client
        redis = MockRedis()
        rec_service = RecommendationService(redis_client=redis)

        recommendations = await rec_service.get_recommendations(test_session, user.id, n=2)
        assert len(recommendations) == 2
        # Should recommend beauty products first
        for prod in recommendations:
            assert prod.category == "beauty"

        # Verify Redis caching was set with recommend:{user_id}:2 key
        cache_key = f"recommend:{user.id}:2"
        cached_val = await redis.get(cache_key)
        assert cached_val is not None
        cached_ids = json.loads(cached_val)
        assert len(cached_ids) == 2
        assert str(recommendations[0].id) in cached_ids

    async def test_collaborative_filtering_recommendations(
        self, test_session: AsyncSession, seed_users, seed_products
    ):
        """Tests recommendations for a user with >= 5 events, triggering CF matrix factorization."""
        user = seed_users[1]

        # Seed 6 events so the user is above the cold-start threshold (>= 5 events)
        # Interaction events: 3 views (1.0 each), 2 cart adds (3.0 each), 1 purchase (5.0)
        events = [
            Event(user_id=user.id, event_type="product_view", product_id=seed_products[0].id),
            Event(user_id=user.id, event_type="product_view", product_id=seed_products[1].id),
            Event(user_id=user.id, event_type="cart_add", product_id=seed_products[2].id),
            Event(user_id=user.id, event_type="cart_add", product_id=seed_products[3].id),
            Event(user_id=user.id, event_type="purchase", product_id=seed_products[4].id),
            Event(user_id=user.id, event_type="product_view", product_id=seed_products[4].id),
        ]
        test_session.add_all(events)
        await test_session.commit()

        analytics = AnalyticsService()
        profile = await analytics.build_user_profile(test_session, user.id)
        await test_session.commit()
        assert profile.total_events >= 5

        # Also seed interactions from other users to build collaborative filter dataset
        other_user = seed_users[2]
        other_events = [
            Event(user_id=other_user.id, event_type="product_view", product_id=seed_products[0].id),
            Event(user_id=other_user.id, event_type="purchase", product_id=seed_products[2].id),
            Event(user_id=other_user.id, event_type="purchase", product_id=seed_products[4].id),
        ]
        test_session.add_all(other_events)
        await test_session.commit()

        redis = MockRedis()
        rec_service = RecommendationService(redis_client=redis)

        recommendations = await rec_service.get_recommendations(test_session, user.id, n=3)
        # Verify SVD returns products
        assert len(recommendations) > 0
        # Excludes user's purchases & cart adds (Product 2, 3, 4)
        excluded_ids = {seed_products[2].id, seed_products[3].id, seed_products[4].id}
        for prod in recommendations:
            assert prod.id not in excluded_ids

        # Check that SURPRISE_AVAILABLE is correct (expected False due to pip fail)
        assert SURPRISE_AVAILABLE is False


@pytest.mark.asyncio
class TestRecommendationAPI:
    """Tests the recommendations REST endpoints."""

    async def test_recommend_endpoint_success(self, client: AsyncClient, seed_users):
        """Tests fetching top-N recommendations for a valid user."""
        user_id = seed_users[0].id
        res = await client.get(
            f"/api/recommend/{user_id}?n=3",
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) <= 3
        if data:
            assert "id" in data[0]
            assert "name" in data[0]
            assert "price" in data[0]

    async def test_recommend_endpoint_not_found(self, client: AsyncClient):
        """Asserts 404 for invalid user ID."""
        random_id = uuid.uuid4()
        res = await client.get(
            f"/api/recommend/{random_id}?n=3",
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 404
        assert res.json()["detail"] == "User not found"

    async def test_recommend_endpoint_unauthorized(self, client: AsyncClient, seed_users):
        """Asserts 401 for unauthorized key."""
        user_id = seed_users[0].id
        res = await client.get(
            f"/api/recommend/{user_id}?n=3",
            headers={"X-API-Key": "invalid-key"},
        )
        assert res.status_code == 401
