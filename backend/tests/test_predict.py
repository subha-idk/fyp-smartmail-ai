"""Tests for Phase 4: ML Prediction Module."""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db, get_redis
from app.main import app
from app.services.ml_service import MLService
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
class TestMLService:
    """Tests the MLService metrics calculations and predictions."""

    async def test_predict_methods_and_run_full_prediction(
        self, test_session: AsyncSession, seed_users
    ):
        user = seed_users[0]
        ml_service = MLService()

        # Feature dictionary matching MLService requirements
        features = {
            "days_since_last_active": 5,
            "days_since_last_purchase": 10,
            "total_events_7d": 15,
            "total_events_30d": 30,
            "total_purchases": 5,
            "total_spend": 100.0,
            "cart_add_count_30d": 3,
            "purchase_count_30d": 2,
            "engagement_score": 75.5,
            "rfm_recency": 10,
            "rfm_frequency": 5,
            "rfm_monetary": 100.0,
        }

        # Predict churn risk
        churn_risk = await ml_service.predict_churn(features)
        assert isinstance(churn_risk, float)
        assert 0.0 <= churn_risk <= 1.0

        # Predict intent prob
        intent_prob = await ml_service.predict_purchase_intent(features)
        assert isinstance(intent_prob, float)
        assert 0.0 <= intent_prob <= 1.0

        # Test full prediction pipeline which updates DB profile risk scores
        result = await ml_service.run_full_prediction(test_session, user.id)
        assert result["user_id"] == str(user.id)
        assert "churn_risk" in result
        assert "purchase_probability" in result


@pytest.mark.asyncio
class TestPredictionAPI:
    """Tests the ML Prediction REST endpoints."""

    async def test_predict_endpoint_success(self, client: AsyncClient, seed_users):
        """Tests triggering predictive inference successfully for a valid user."""
        user_id = seed_users[0].id
        res = await client.post(
            f"/api/predict/{user_id}",
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["user_id"] == str(user_id)
        assert "churn_risk" in data
        assert "purchase_probability" in data

    async def test_predict_endpoint_not_found(self, client: AsyncClient):
        """Asserts 404 for invalid user ID."""
        random_id = uuid.uuid4()
        res = await client.post(
            f"/api/predict/{random_id}",
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 404
        assert res.json()["detail"] == "User not found"

    async def test_predict_endpoint_unauthorized(self, client: AsyncClient, seed_users):
        """Asserts 401 for unauthorized API Key."""
        user_id = seed_users[0].id
        res = await client.post(
            f"/api/predict/{user_id}",
            headers={"X-API-Key": "invalid-key"},
        )
        assert res.status_code == 401
