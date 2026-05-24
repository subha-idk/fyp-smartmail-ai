"""Tests for Phase 7: AI Email Generator."""

import uuid
from unittest.mock import MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db, get_redis
from app.main import app
from app.models.product import Product
from app.models.user_profile import UserProfile
from app.models.email_log import EmailLog
from app.services.llm_service import LLMService
from tests.test_track import MockRedis


@pytest.fixture
def mock_redis():
    return MockRedis()


@pytest.fixture
async def client(test_session: AsyncSession, mock_redis: MockRedis) -> AsyncClient:
    """Provides an AsyncClient pointing to the FastAPI app with overridden database session and redis."""
    app.dependency_overrides[get_db] = lambda: test_session
    app.dependency_overrides[get_redis] = lambda: mock_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class MockUsageMetadata:
    def __init__(self, token_count):
        self.total_token_count = token_count


class MockResponse:
    def __init__(self, text, token_count=142):
        self.text = text
        self.usage_metadata = MockUsageMetadata(token_count)


@pytest.mark.asyncio
class TestLLMService:
    """Tests the AI LLMService email generation, sanitization, and fallbacks."""

    async def test_generate_email_success(self, test_session: AsyncSession, seed_users, seed_products):
        """Verifies Gemini successful generation path parsing JSON cleanly."""
        user = seed_users[0]
        product = seed_products[0]
        
        # Create user profile first
        profile = UserProfile(user_id=user.id)
        test_session.add(profile)
        await test_session.flush()
        
        # Load user profile
        stmt = select(UserProfile).where(UserProfile.user_id == user.id)
        res = await test_session.execute(stmt)
        profile = res.scalar_one()

        llm_service = LLMService(db=test_session)

        # Mock response JSON
        success_json = '{"subject": "Hello Test User 1", "html_body": "<p>Check this out</p>", "plain_body": "Check this out"}'
        mock_response = MockResponse(success_json, token_count=150)

        with patch("google.generativeai.GenerativeModel.generate_content", return_value=mock_response) as mock_gen:
            result = await llm_service.generate_email(profile, product, "recommendation")
            
            assert mock_gen.called
            assert result["subject"] == f"Hello {user.name}"
            assert result["html_body"] == "<p>Check this out</p>"
            assert result["plain_body"] == "Check this out"
            assert result["tokens_used"] == 150

            # Verify that email log was written to database
            log_stmt = select(EmailLog).where(EmailLog.user_id == user.id)
            log_res = await test_session.execute(log_stmt)
            logs = log_res.scalars().all()
            assert len(logs) > 0
            assert logs[-1].tokens_used == 150
            assert logs[-1].subject == f"Hello {user.name}"

    async def test_generate_email_code_fences(self, test_session: AsyncSession, seed_users, seed_products):
        """Verifies that markdown code fences (```json ... ```) are correctly stripped."""
        user = seed_users[0]
        product = seed_products[0]
        
        # Create user profile first
        profile = UserProfile(user_id=user.id)
        test_session.add(profile)
        await test_session.flush()
        
        stmt = select(UserProfile).where(UserProfile.user_id == user.id)
        res = await test_session.execute(stmt)
        profile = res.scalar_one()

        llm_service = LLMService(db=test_session)

        # Mock response wrapped in markdown code fence
        fenced_json = '```json\n{"subject": "Exclusive offer!", "html_body": "<div>Hi</div>", "plain_body": "Hi"}\n```'
        mock_response = MockResponse(fenced_json, token_count=180)

        with patch("google.generativeai.GenerativeModel.generate_content", return_value=mock_response):
            result = await llm_service.generate_email(profile, product, "recommendation")
            
            assert result["subject"] == "Exclusive offer!"
            assert result["html_body"] == "<div>Hi</div>"
            assert result["plain_body"] == "Hi"
            assert result["tokens_used"] == 180

    async def test_generate_email_malformed_json_fallback(self, test_session: AsyncSession, seed_users, seed_products):
        """Verifies fallback handles malformed JSON response from Gemini (e.g. conversational preamble)."""
        user = seed_users[0]
        product = seed_products[0]
        
        # Create user profile first
        profile = UserProfile(user_id=user.id)
        test_session.add(profile)
        await test_session.flush()
        
        stmt = select(UserProfile).where(UserProfile.user_id == user.id)
        res = await test_session.execute(stmt)
        profile = res.scalar_one()

        llm_service = LLMService(db=test_session)

        # Mock malformed response
        malformed_response = "Sure! Here is your email: {invalid}"
        mock_response = MockResponse(malformed_response, token_count=50)

        with patch("google.generativeai.GenerativeModel.generate_content", return_value=mock_response):
            result = await llm_service.generate_email(profile, product, "recommendation")
            
            # Should not raise exception, should return fallback
            assert result["tokens_used"] == 0
            assert len(result["subject"]) > 0
            assert len(result["plain_body"]) > 0
            assert "<html>" in result["html_body"]

            # Verify that email log was written to database with 0 tokens_used
            log_stmt = select(EmailLog).where(EmailLog.user_id == user.id)
            log_res = await test_session.execute(log_stmt)
            logs = log_res.scalars().all()
            assert len(logs) > 0
            assert logs[-1].tokens_used == 0

    async def test_generate_email_exception_fallback(self, test_session: AsyncSession, seed_users, seed_products):
        """Verifies fallback operates when Gemini SDK triggers an exception."""
        user = seed_users[0]
        product = seed_products[0]
        
        # Create user profile first
        profile = UserProfile(user_id=user.id)
        test_session.add(profile)
        await test_session.flush()
        
        stmt = select(UserProfile).where(UserProfile.user_id == user.id)
        res = await test_session.execute(stmt)
        profile = res.scalar_one()

        llm_service = LLMService(db=test_session)

        # Force exception
        with patch("google.generativeai.GenerativeModel.generate_content", side_effect=RuntimeError("API failure")):
            result = await llm_service.generate_email(profile, product, "recommendation")
            
            assert result["tokens_used"] == 0
            assert "Handpicked recommendations" in result["subject"]
            assert user.name in result["plain_body"]
            assert "<html>" in result["html_body"]


@pytest.mark.asyncio
class TestGenerateEmailAPI:
    """Tests the /api/generate-email REST endpoint."""

    async def test_generate_endpoint_success(self, client: AsyncClient, seed_users, seed_products):
        """Tests triggering generating email through endpoint."""
        user = seed_users[0]
        product = seed_products[0]
        
        success_json = '{"subject": "Special offer for Test User 1", "html_body": "<p>Check it out</p>", "plain_body": "Check it out"}'
        mock_response = MockResponse(success_json, token_count=142)

        with patch("google.generativeai.GenerativeModel.generate_content", return_value=mock_response):
            payload = {
                "user_id": str(user.id),
                "email_type": "recommendation",
                "product_id": str(product.id)
            }
            res = await client.post(
                "/api/generate-email",
                json=payload,
                headers={"X-API-Key": settings.API_SECRET_KEY},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["subject"] == f"Special offer for {user.name}"
            assert data["tokens_used"] == 142

    async def test_generate_endpoint_not_found(self, client: AsyncClient):
        """Asserts 404 on invalid user."""
        payload = {
            "user_id": str(uuid.uuid4()),
            "email_type": "recommendation"
        }
        res = await client.post(
            "/api/generate-email",
            json=payload,
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 404
