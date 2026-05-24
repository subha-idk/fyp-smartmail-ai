"""Tests for Phase 6: Decision Engine."""

import uuid
from datetime import UTC, datetime, timedelta
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db, get_redis
from app.main import app
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.event import Event
from app.services.decision_service import DecisionService
from tests.test_track import MockRedis


@pytest.fixture
async def client(test_session: AsyncSession, mock_redis: MockRedis) -> AsyncClient:
    """Provides an AsyncClient pointing to the FastAPI app with overridden dependencies."""
    app.dependency_overrides[get_db] = lambda: test_session
    app.dependency_overrides[get_redis] = lambda: mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_redis():
    return MockRedis()


@pytest.mark.asyncio
class TestDecisionService:
    """Tests the campaign DecisionService business logic."""

    async def test_cooldown_set_and_checked(self, test_session: AsyncSession, seed_users, mock_redis):
        """Verifies that the cooldown is successfully set in Redis and blocks decisions."""
        user = seed_users[0]
        service = DecisionService(redis_client=mock_redis)

        # Initially false
        assert await service.check_cooldown(user.id) is False

        # Set cooldown
        await service.set_cooldown(user.id)

        # Verify key is set in Redis directly
        redis_val = await mock_redis.get(f"cooldown:{user.id}")
        assert redis_val == "1"

        # Verify check_cooldown is True
        assert await service.check_cooldown(user.id) is True

        # Verify decision service skips due to cooldown
        decision = await service.decide_email_type(test_session, user.id)
        assert decision["email_type"] is None
        assert decision["cooldown_active"] is True
        assert decision["skip_reason"] == "cooldown_active"

    async def test_cooldown_set_on_decision(self, test_session: AsyncSession, seed_users, mock_redis):
        """Verifies that the cooldown is SET in Redis after a campaign decision is made."""
        user = seed_users[0]
        profile = UserProfile(user_id=user.id)
        test_session.add(profile)
        await test_session.flush()

        service = DecisionService(redis_client=mock_redis)
        assert await mock_redis.get(f"cooldown:{user.id}") is None

        decision = await service.decide_email_type(test_session, user.id)
        assert decision["email_type"] == "recommendation"
        assert await mock_redis.get(f"cooldown:{user.id}") == "1"

    async def test_churn_priority(self, test_session: AsyncSession, seed_users, mock_redis):
        """Rule 2: Churn risk > threshold -> retention."""
        user = seed_users[0]
        profile = UserProfile(user_id=user.id)
        test_session.add(profile)
        await test_session.flush()

        # Query profile
        stmt = select(UserProfile).where(UserProfile.user_id == user.id)
        res = await test_session.execute(stmt)
        profile = res.scalar_one()
        
        # Set churn risk above threshold
        profile.churn_risk = settings.CHURN_RISK_THRESHOLD + 0.05
        await test_session.commit()

        service = DecisionService(redis_client=mock_redis)
        # Clear cooldown from previous write (since decide_email_type now sets it)
        # But wait, here we are evaluating decide_email_type which would set cooldown, which is fine
        decision = await service.decide_email_type(test_session, user.id)
        assert decision["email_type"] == "retention"
        assert "churn_risk" in decision["rationale"]

    async def test_abandoned_cart_priority(self, test_session: AsyncSession, seed_users, seed_products, mock_redis):
        """Rule 3: Cart abandoned > CART_ABANDON_HOURS -> abandoned_cart."""
        user = seed_users[0]
        product = seed_products[0]
        profile = UserProfile(user_id=user.id)
        test_session.add(profile)
        await test_session.flush()

        # Reset profile thresholds so they don't block
        stmt = select(UserProfile).where(UserProfile.user_id == user.id)
        res = await test_session.execute(stmt)
        profile = res.scalar_one()
        profile.churn_risk = settings.CHURN_RISK_THRESHOLD - 0.1
        profile.purchase_probability = settings.PURCHASE_PROB_THRESHOLD - 0.1
        profile.total_spend = settings.TOP_SPENDER_THRESHOLD - 100.0
        profile.days_since_last_purchase = None
        await test_session.commit()

        # Add cart_add event in the past (> CART_ABANDON_HOURS)
        abandon_time = datetime.now(UTC) - timedelta(hours=settings.CART_ABANDON_HOURS + 1)
        event = Event(
            user_id=user.id,
            event_type="cart_add",
            product_id=product.id,
            timestamp=abandon_time
        )
        test_session.add(event)
        await test_session.commit()

        service = DecisionService(redis_client=mock_redis)
        decision = await service.decide_email_type(test_session, user.id)
        assert decision["email_type"] == "abandoned_cart"
        assert "Abandoned cart" in decision["rationale"]

    async def test_purchase_probability_priority(self, test_session: AsyncSession, seed_users, mock_redis):
        """Rule 4: Purchase probability > threshold -> recommendation."""
        user = seed_users[0]
        profile = UserProfile(user_id=user.id)
        test_session.add(profile)
        await test_session.flush()

        stmt = select(UserProfile).where(UserProfile.user_id == user.id)
        res = await test_session.execute(stmt)
        profile = res.scalar_one()
        
        # Reset other higher priority rules
        profile.churn_risk = settings.CHURN_RISK_THRESHOLD - 0.1
        profile.total_spend = settings.TOP_SPENDER_THRESHOLD - 100.0
        profile.days_since_last_purchase = None
        
        # Set purchase probability
        profile.purchase_probability = settings.PURCHASE_PROB_THRESHOLD + 0.05
        await test_session.commit()

        service = DecisionService(redis_client=mock_redis)
        decision = await service.decide_email_type(test_session, user.id)
        assert decision["email_type"] == "recommendation"
        assert "purchase_probability" in decision["rationale"]

    async def test_top_spender_priority(self, test_session: AsyncSession, seed_users, mock_redis):
        """Rule 5: Spend > threshold -> upsell."""
        user = seed_users[0]
        profile = UserProfile(user_id=user.id)
        test_session.add(profile)
        await test_session.flush()

        stmt = select(UserProfile).where(UserProfile.user_id == user.id)
        res = await test_session.execute(stmt)
        profile = res.scalar_one()
        
        # Reset higher priority rules
        profile.churn_risk = settings.CHURN_RISK_THRESHOLD - 0.1
        profile.purchase_probability = settings.PURCHASE_PROB_THRESHOLD - 0.1
        profile.days_since_last_purchase = None
        
        # Set total spend
        profile.total_spend = settings.TOP_SPENDER_THRESHOLD + 50.0
        await test_session.commit()

        service = DecisionService(redis_client=mock_redis)
        decision = await service.decide_email_type(test_session, user.id)
        assert decision["email_type"] == "upsell"
        assert "total_spend" in decision["rationale"]

    async def test_review_request_priority(self, test_session: AsyncSession, seed_users, mock_redis):
        """Rule 6: Last purchase 7-14 days ago -> review_request."""
        user = seed_users[0]
        profile = UserProfile(user_id=user.id)
        test_session.add(profile)
        await test_session.flush()

        stmt = select(UserProfile).where(UserProfile.user_id == user.id)
        res = await test_session.execute(stmt)
        profile = res.scalar_one()
        
        # Reset higher priority rules
        profile.churn_risk = settings.CHURN_RISK_THRESHOLD - 0.1
        profile.purchase_probability = settings.PURCHASE_PROB_THRESHOLD - 0.1
        profile.total_spend = settings.TOP_SPENDER_THRESHOLD - 100.0
        
        # Set purchase window recency
        profile.days_since_last_purchase = 10
        await test_session.commit()

        service = DecisionService(redis_client=mock_redis)
        decision = await service.decide_email_type(test_session, user.id)
        assert decision["email_type"] == "review_request"
        assert "Last purchase was 10 days ago" in decision["rationale"]

    async def test_default_recommendation(self, test_session: AsyncSession, seed_users, mock_redis):
        """Rule 7: Fallback -> recommendation."""
        user = seed_users[0]
        profile = UserProfile(user_id=user.id)
        test_session.add(profile)
        await test_session.flush()

        stmt = select(UserProfile).where(UserProfile.user_id == user.id)
        res = await test_session.execute(stmt)
        profile = res.scalar_one()
        
        # Reset all rules
        profile.churn_risk = settings.CHURN_RISK_THRESHOLD - 0.1
        profile.purchase_probability = settings.PURCHASE_PROB_THRESHOLD - 0.1
        profile.total_spend = settings.TOP_SPENDER_THRESHOLD - 100.0
        profile.days_since_last_purchase = 20
        await test_session.commit()

        service = DecisionService(redis_client=mock_redis)
        decision = await service.decide_email_type(test_session, user.id)
        assert decision["email_type"] == "recommendation"
        assert "Default" in decision["rationale"]


@pytest.mark.asyncio
class TestDecisionAPI:
    """Tests the Decision API router endpoints."""

    async def test_decide_endpoint_success(self, client: AsyncClient, seed_users):
        """Verifies endpoint evaluates decision and returns expected payload structure."""
        user_id = seed_users[0].id
        res = await client.post(
            f"/api/decide/{user_id}",
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 200
        data = res.json()
        assert "email_type" in data
        assert "rationale" in data
        assert "cooldown_active" in data
        assert "skip_reason" in data

    async def test_decide_endpoint_not_found(self, client: AsyncClient):
        """Asserts 404 on non-existent user."""
        random_id = uuid.uuid4()
        res = await client.post(
            f"/api/decide/{random_id}",
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 404
        assert res.json()["detail"] == "User not found"
