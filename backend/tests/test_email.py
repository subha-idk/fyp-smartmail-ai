"""Tests for Phase 8: Email Delivery Service and Send-Email Endpoint."""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import patch, AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db, get_redis
from app.main import app
from app.models.email_log import EmailLog
from app.models.user_profile import UserProfile
from app.services.email_service import EmailService
from tests.test_generate import MockResponse


class MockRedis:
    """Mock Redis client for testing stream ingestion and rate limiting."""

    def __init__(self):
        self.messages = []
        self.expired = {}
        self.counts = {}
        self.acked = []
        self.kv = {}

    async def get(self, key):
        return self.kv.get(key)

    async def exists(self, *keys):
        count = 0
        for k in keys:
            if k in self.kv:
                count += 1
        return count

    async def set(self, key, value):
        self.kv[key] = value
        return True

    async def setex(self, key, seconds, value):
        self.kv[key] = value
        self.expired[key] = seconds
        return True

    async def delete(self, *keys):
        deleted_count = 0
        for k in keys:
            if k in self.kv:
                del self.kv[k]
                deleted_count += 1
        return deleted_count

    async def xadd(self, stream, data):
        self.messages.append((stream, data))
        return "123-0"

    async def xack(self, stream, group, *ids):
        self.acked.extend(ids)
        return len(ids)

    def pipeline(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def execute(self):
        return []

    async def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key, seconds):
        self.expired[key] = seconds
        return True


@pytest.fixture
def mock_redis():
    return MockRedis()


@pytest.fixture
async def client(test_session: AsyncSession, mock_redis) -> AsyncClient:
    """Provides an AsyncClient pointing to the FastAPI app with overridden dependencies."""
    app.dependency_overrides[get_db] = lambda: test_session
    app.dependency_overrides[get_redis] = lambda: mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestEmailDeliveryRouterAndPipeline:
    """Tests the /api/send-email/{user_id} endpoint and corresponding pipeline execution."""

    async def test_send_email_missing_auth(self, client: AsyncClient, seed_users):
        """Asserts 401 response on missing API Key."""
        res = await client.post(f"/api/send-email/{seed_users[0].id}")
        assert res.status_code == 401

    async def test_send_email_not_found(self, client: AsyncClient):
        """Asserts 404 response on non-existent user."""
        res = await client.post(
            f"/api/send-email/{uuid.uuid4()}",
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"]

    async def test_send_email_success(
        self, client: AsyncClient, test_session: AsyncSession, mock_redis, seed_users, seed_products
    ):
        """Verify successful email pipeline flow and DB/Redis updates."""
        user = seed_users[0]
        product = seed_products[0]

        # Ensure user profile exists
        profile = UserProfile(user_id=user.id, last_active_at=datetime.now(UTC))
        test_session.add(profile)
        await test_session.flush()

        success_json = '{"subject": "Special Deal", "html_body": "<html><body>Shop here: <a href=\'http://example.com/item\'>Item</a></body></html>", "plain_body": "Shop here: http://example.com/item"}'
        mock_resp = MockResponse(success_json, token_count=100)

        # Mock both the LLM generation and the active send dispatcher
        with patch("google.generativeai.GenerativeModel.generate_content", return_value=mock_resp), \
             patch("app.services.email_service.EmailService.send", new_callable=AsyncMock) as mock_send:

            res = await client.post(
                f"/api/send-email/{user.id}",
                headers={"X-API-Key": settings.API_SECRET_KEY},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "sent"
            assert data["email_type"] is not None
            assert data["subject"] == "Special Deal"
            assert "log_id" in data

            # Verify mock_send arguments
            assert mock_send.call_count == 1
            _, kwargs = mock_send.call_args
            assert kwargs["to_email"] == user.email
            assert kwargs["subject"] == "Special Deal"
            html_body_sent = kwargs["html_body"]

            # Check tracking pixel and click URL injection in the sent HTML
            assert "/api/track/open/" in html_body_sent
            assert "/api/track/click/" in html_body_sent
            assert "redirect=http://example.com/item" in html_body_sent

            # Verify email log record in Postgres
            log_id = uuid.UUID(data["log_id"])
            stmt = select(EmailLog).where(EmailLog.id == log_id)
            log_res = await test_session.execute(stmt)
            log = log_res.scalar_one_or_none()
            assert log is not None
            assert log.status == "sent"
            assert log.open_token is not None
            assert log.click_token is not None

            # Verify Redis Cooldown is set
            cooldown_key = f"cooldown:{user.id}"
            assert await mock_redis.get(cooldown_key) == "1"

    async def test_send_email_cooldown_skip(
        self, client: AsyncClient, test_session: AsyncSession, mock_redis, seed_users
    ):
        """Verify that email pipeline skips sending if cooldown is active."""
        user = seed_users[0]

        # Ensure user profile exists
        profile = UserProfile(user_id=user.id, last_active_at=datetime.now(UTC))
        test_session.add(profile)
        await test_session.flush()

        # Set active cooldown in Redis
        cooldown_key = f"cooldown:{user.id}"
        await mock_redis.set(cooldown_key, "1")

        res = await client.post(
            f"/api/send-email/{user.id}",
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "skipped"
        assert data["reason"] == "cooldown"

    async def test_send_email_failure_removes_cooldown(
        self, client: AsyncClient, test_session: AsyncSession, mock_redis, seed_users, seed_products
    ):
        """Verify pipeline failure sets status to failed and removes/does not write cooldown."""
        user = seed_users[0]
        product = seed_products[0]

        # Ensure user profile exists
        profile = UserProfile(user_id=user.id, last_active_at=datetime.now(UTC))
        test_session.add(profile)
        await test_session.flush()

        success_json = '{"subject": "Special Deal", "html_body": "<html><body>Body</body></html>", "plain_body": "Body"}'
        mock_resp = MockResponse(success_json, token_count=100)

        # Force exception during send
        with patch("google.generativeai.GenerativeModel.generate_content", return_value=mock_resp), \
             patch("app.services.email_service.EmailService.send", side_effect=Exception("SMTP Connection Lost")):

            res = await client.post(
                f"/api/send-email/{user.id}",
                headers={"X-API-Key": settings.API_SECRET_KEY},
            )
            assert res.status_code == 500
            assert "Email dispatch pipeline failed" in res.json()["detail"]

            # Verify Redis cooldown key is NOT set (or deleted)
            cooldown_key = f"cooldown:{user.id}"
            assert await mock_redis.get(cooldown_key) is None

            # Verify database record updated to status failed
            stmt = select(EmailLog).where(EmailLog.user_id == user.id)
            log_res = await test_session.execute(stmt)
            logs = log_res.scalars().all()
            assert len(logs) > 0
            assert logs[-1].status == "failed"


class TestEmailServiceTrackingInjection:
    """Tests only the tracking injection HTML manipulation routines."""

    def test_inject_tracking_pixel_and_links(self):
        service = EmailService()
        html_input = """
        <html>
        <head><title>Test</title></head>
        <body>
            <h1>Hello</h1>
            <p>Click <a href="http://google.com">here</a> or <a href="#hash">anchor</a>.</p>
            <p>Already tracked: <a href="http://localhost:8000/api/track/click/token?redirect=http://google.com">tracked</a></p>
        </body>
        </html>
        """

        open_token = "open123"
        click_token = "click456"

        output = service.inject_tracking(html_input, open_token, click_token)

        # Verify open tracking pixel before </body>
        assert '<img src="http://localhost:8000/api/track/open/open123" width="1" height="1" style="display:none" />' in output
        assert '</body>' in output

        # Verify link replacement
        assert 'href="http://localhost:8000/api/track/click/click456?redirect=http://google.com"' in output
        # Hash links must be left intact
        assert 'href="#hash"' in output
        # Already tracked links must be left intact
        assert 'href="http://localhost:8000/api/track/click/token?redirect=http://google.com"' in output


class TestEmailLogsAndHealthEndpoints:
    """Tests the GET /api/email_logs and GET /api/health API endpoints."""

    async def test_api_health_endpoint(self, client: AsyncClient):
        """Asserts GET /api/health returns status: ok without authentication."""
        res = await client.get("/api/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

    async def test_get_email_logs_missing_auth(self, client: AsyncClient):
        """Asserts 401 response on missing API Key."""
        res = await client.get("/api/email_logs")
        assert res.status_code == 401

    async def test_get_email_logs_success(
        self, client: AsyncClient, test_session: AsyncSession, seed_users
    ):
        """Asserts correct retrieval of paginated email logs with user details."""
        user = seed_users[0]
        # Seed 3 email logs for user
        for i in range(3):
            log = EmailLog(
                user_id=user.id,
                email_type="retention",
                subject=f"Retention Subject {i}",
                status="sent",
                tokens_used=150 + i,
            )
            test_session.add(log)
        await test_session.flush()

        res = await client.get(
            "/api/email_logs?page=1&limit=2",
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 3
        assert len(data["logs"]) == 2

        # Verify first log
        log0 = data["logs"][0]
        assert log0["user_id"] == str(user.id)
        assert log0["user_name"] == user.name
        assert log0["user_email"] == user.email
        assert "tokens_used" in log0

