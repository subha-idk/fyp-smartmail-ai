"""Tests for Phase 9: Feedback Loop Tracking and Idempotence."""

import json
import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db, get_redis
from app.main import app
from app.models.email_log import EmailLog
from tests.test_track import MockRedis


@pytest.fixture
def mock_redis():
    return MockRedis()


@pytest.fixture
async def client(test_session: AsyncSession, mock_redis) -> AsyncClient:
    """Provides an AsyncClient pointing to the FastAPI app with overridden database and redis dependencies."""
    app.dependency_overrides[get_db] = lambda: test_session
    app.dependency_overrides[get_redis] = lambda: mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestFeedbackLoopTracking:
    """Tests email open and click tracking with idempotency and 404 validations."""

    async def test_track_open_404_invalid_token(self, client: AsyncClient):
        """Asserts HTTP 404 when track open token does not exist in DB."""
        res = await client.get("/api/track/open/invalid-token")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    async def test_track_open_success_and_idempotency(
        self, client: AsyncClient, test_session: AsyncSession, mock_redis, seed_users
    ):
        """Tests that track open sets opened_at, queues event, and consecutive hits return pixel without re-enqueueing."""
        user = seed_users[0]
        log = EmailLog(
            user_id=user.id,
            email_type="retention",
            open_token="open-token-xyz",
            status="sent",
        )
        test_session.add(log)
        await test_session.commit()

        # First hit
        res = await client.get("/api/track/open/open-token-xyz")
        assert res.status_code == 200
        assert res.headers["content-type"] == "image/gif"

        # Verify DB updated
        await test_session.refresh(log)
        assert log.status == "opened"
        assert log.opened_at is not None

        # Verify event enqueued in mock Redis
        assert len(mock_redis.messages) == 1
        stream, msg_data = mock_redis.messages[0]
        assert stream == "events:raw"
        event_payload = json.loads(msg_data["payload"])
        assert event_payload["event_type"] == "email_open"
        assert event_payload["user_id"] == str(user.id)

        # Clear mock redis messages
        mock_redis.messages.clear()

        # Second hit (idempotent duplicate)
        res_dup = await client.get("/api/track/open/open-token-xyz")
        assert res_dup.status_code == 200
        # Verify no additional events enqueued
        assert len(mock_redis.messages) == 0

    async def test_track_click_404_invalid_token(self, client: AsyncClient):
        """Asserts HTTP 404 when track click token does not exist in DB."""
        res = await client.get("/api/track/click/invalid-token?redirect=http://google.com")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    async def test_track_click_success_and_idempotency(
        self, client: AsyncClient, test_session: AsyncSession, mock_redis, seed_users
    ):
        """Tests click redirect returns 302, sets clicked_at, and duplicate hits do not trigger new events."""
        user = seed_users[0]
        log = EmailLog(
            user_id=user.id,
            email_type="recommendation",
            click_token="click-token-xyz",
            status="sent",
        )
        test_session.add(log)
        await test_session.commit()

        target_redirect = "http://google.com/product/123"

        # First click
        res = await client.get(
            f"/api/track/click/click-token-xyz?redirect={target_redirect}", follow_redirects=False
        )
        assert res.status_code == 302
        assert res.headers["location"] == target_redirect

        # Verify DB updated
        await test_session.refresh(log)
        assert log.status == "clicked"
        assert log.clicked_at is not None
        assert log.opened_at is not None

        # Verify click event enqueued
        assert len(mock_redis.messages) == 1
        stream, msg_data = mock_redis.messages[0]
        assert stream == "events:raw"
        event_payload = json.loads(msg_data["payload"])
        assert event_payload["event_type"] == "email_click"

        # Clear mock redis messages
        mock_redis.messages.clear()

        # Second click (idempotent duplicate)
        res_dup = await client.get(
            f"/api/track/click/click-token-xyz?redirect={target_redirect}", follow_redirects=False
        )
        assert res_dup.status_code == 302
        assert res_dup.headers["location"] == target_redirect
        # Verify no duplicate event enqueued
        assert len(mock_redis.messages) == 0
