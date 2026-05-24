"""Tests for Phase 2: Event Ingestion API and Background Worker."""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db, get_redis
from app.main import app
from app.models.email_log import EmailLog
from app.models.event import Event
from app.workers.event_worker import process_batch


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


class MockSessionFactory:
    """Mock database session factory that yields the transactional test session."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


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
class TestTrackAPIAuthAndRateLimit:
    """Tests authentication (X-API-Key) and rate limiting on tracking endpoints."""

    async def test_track_missing_api_key(self, client: AsyncClient, seed_users):
        """Asserts 401 response on missing API Key."""
        payload = {
            "user_id": str(seed_users[0].id),
            "event_type": "product_view",
            "product_id": None,
            "session_id": "test-sess",
            "category": "electronics",
            "metadata": {},
        }
        res = await client.post("/api/track", json=payload)
        assert res.status_code == 401
        assert "Missing API Key" in res.json()["detail"]

    async def test_track_invalid_api_key(self, client: AsyncClient, seed_users):
        """Asserts 401 response on invalid API Key."""
        payload = {
            "user_id": str(seed_users[0].id),
            "event_type": "product_view",
        }
        res = await client.post(
            "/api/track", json=payload, headers={"X-API-Key": "wrong-key"}
        )
        assert res.status_code == 401
        assert "Invalid API Key" in res.json()["detail"]

    async def test_track_rate_limiting(self, client: AsyncClient, mock_redis, seed_users):
        """Asserts 429 response when the rate limit threshold (1000) is exceeded."""
        payload = {
            "user_id": str(seed_users[0].id),
            "event_type": "product_view",
        }
        # Fake rate limit state to exceed 1000
        current_minute = int(datetime.now(UTC).timestamp()) // 60
        key = f"rate_limit:{settings.API_SECRET_KEY}:{current_minute}"
        mock_redis.counts[key] = 1000  # next incr will make it 1001

        res = await client.post(
            "/api/track",
            json=payload,
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 429
        assert "Rate limit exceeded" in res.json()["detail"]


@pytest.mark.asyncio
class TestEventIngestion:
    """Tests single and batch event ingestion endpoints."""

    async def test_ingest_single_event_success(
        self, client: AsyncClient, mock_redis, seed_users
    ):
        """Successfully ingests a single event and enqueues to Redis."""
        payload = {
            "user_id": str(seed_users[0].id),
            "event_type": "product_view",
            "session_id": "sess-xyz",
            "category": "fashion",
        }
        res = await client.post(
            "/api/track",
            json=payload,
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 202
        data = res.json()
        assert data["status"] == "queued"
        assert "event_id" in data

        # Verify Redis enqueuing
        assert len(mock_redis.messages) == 1
        stream, msg_data = mock_redis.messages[0]
        assert stream == "events:raw"
        stream_payload = json.loads(msg_data["payload"])
        assert stream_payload["user_id"] == str(seed_users[0].id)
        assert stream_payload["event_type"] == "product_view"
        assert stream_payload["session_id"] == "sess-xyz"
        assert stream_payload["category"] == "fashion"

    async def test_ingest_batch_events_success(
        self, client: AsyncClient, mock_redis, seed_users
    ):
        """Successfully ingests multiple events under the maximum limit."""
        payloads = [
            {
                "user_id": str(seed_users[0].id),
                "event_type": "search",
                "category": "beauty",
            },
            {
                "user_id": str(seed_users[1].id),
                "event_type": "cart_add",
                "session_id": "sess-2",
            },
        ]
        res = await client.post(
            "/api/track/batch",
            json=payloads,
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 200
        assert res.json() == {"queued": 2, "failed": 0}
        assert len(mock_redis.messages) == 2

    async def test_ingest_batch_limit_exceeded(self, client: AsyncClient, seed_users):
        """Asserts 400 response when batch size exceeds 100 events."""
        payloads = [
            {"user_id": str(seed_users[0].id), "event_type": "search"}
            for _ in range(101)
        ]
        res = await client.post(
            "/api/track/batch",
            json=payloads,
            headers={"X-API-Key": settings.API_SECRET_KEY},
        )
        assert res.status_code == 400
        assert "exceeds maximum limit" in res.json()["detail"]


@pytest.mark.asyncio
class TestPublicTracking:
    """Tests the public tracking pixel and click redirects endpoints."""

    async def test_email_open_pixel_success(
        self, client: AsyncClient, test_session: AsyncSession, mock_redis, seed_users
    ):
        """Fires tracking pixel, updates EmailLog to opened, and enqueues event."""
        # Create EmailLog record first
        log = EmailLog(
            user_id=seed_users[0].id,
            email_type="retention",
            open_token="open-token-123",
            status="sent",
        )
        test_session.add(log)
        await test_session.commit()

        res = await client.get("/api/track/open/open-token-123")
        assert res.status_code == 200
        assert res.headers["content-type"] == "image/gif"
        assert res.headers["cache-control"] == "no-cache, no-store, must-revalidate"

        # Verify DB update
        await test_session.refresh(log)
        assert log.status == "opened"
        assert log.opened_at is not None

        # Verify Redis enqueuing of email_open event
        assert len(mock_redis.messages) == 1
        stream, msg_data = mock_redis.messages[0]
        assert stream == "events:raw"
        stream_payload = json.loads(msg_data["payload"])
        assert stream_payload["event_type"] == "email_open"
        assert stream_payload["user_id"] == str(seed_users[0].id)

    async def test_email_click_redirect_success(
        self, client: AsyncClient, test_session: AsyncSession, mock_redis, seed_users
    ):
        """Fires redirect, updates EmailLog to clicked, and enqueues email_click event."""
        # Create EmailLog record first
        log = EmailLog(
            user_id=seed_users[0].id,
            email_type="upsell",
            click_token="click-token-123",
            status="sent",
        )
        test_session.add(log)
        await test_session.commit()

        target_url = "https://example.com/product/456"
        res = await client.get(
            f"/api/track/click/click-token-123?redirect={target_url}",
            follow_redirects=False,
        )
        # Redirection test
        assert res.status_code == 302
        assert res.headers["location"] == target_url

        # Verify DB updates
        await test_session.refresh(log)
        assert log.status == "clicked"
        assert log.clicked_at is not None
        assert log.opened_at is not None

        # Verify Redis enqueuing of email_click event
        assert len(mock_redis.messages) == 1
        stream, msg_data = mock_redis.messages[0]
        assert stream == "events:raw"
        stream_payload = json.loads(msg_data["payload"])
        assert stream_payload["event_type"] == "email_click"
        assert stream_payload["user_id"] == str(seed_users[0].id)


@pytest.mark.asyncio
class TestEventWorker:
    """Tests the processing and persistence logic of the background worker."""

    async def test_worker_process_batch_success(
        self, test_session: AsyncSession, seed_users, seed_products
    ):
        """Processes valid event batch successfully and persists to Postgres."""
        mock_redis = MockRedis()

        event_1_id = uuid.uuid4()
        event_2_id = uuid.uuid4()

        payload_1 = {
            "id": str(event_1_id),
            "user_id": str(seed_users[0].id),
            "event_type": "product_view",
            "product_id": str(seed_products[0].id),
            "session_id": "sess-worker-1",
            "category": seed_products[0].category,
            "metadata": {},
            "timestamp": datetime.now(UTC).isoformat(),
        }
        payload_2 = {
            "id": str(event_2_id),
            "user_id": str(seed_users[1].id),
            "event_type": "purchase",
            "product_id": str(seed_products[1].id),
            "session_id": "sess-worker-2",
            "category": seed_products[1].category,
            "metadata": {"source": "web"},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        batch = [
            ("msg-1", json.dumps(payload_1)),
            ("msg-2", json.dumps(payload_2)),
        ]

        with patch(
            "app.workers.event_worker.async_session_factory",
            MockSessionFactory(test_session),
        ):
            await process_batch(mock_redis, batch)

        # Verify events are written to database
        db_events = (
            await test_session.execute(
                select(Event).where(Event.id.in_([event_1_id, event_2_id]))
            )
        ).scalars().all()

        assert len(db_events) == 2
        event_map = {e.id: e for e in db_events}
        assert event_map[event_1_id].event_type == "product_view"
        assert event_map[event_2_id].event_type == "purchase"
        assert event_map[event_2_id].metadata_ == {"source": "web"}

        # Verify Redis messages are ACKed
        assert "msg-1" in mock_redis.acked
        assert "msg-2" in mock_redis.acked

    async def test_worker_process_batch_failure_routing(
        self, test_session: AsyncSession, seed_users
    ):
        """Routes invalid events in batch to the dead-letter stream, while acknowledging them."""
        mock_redis = MockRedis()

        # Invalid user_id (not in database) -> will cause ForeignKey constraint failure
        invalid_payload = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "event_type": "product_view",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Structurally invalid event (missing user_id, invalid json format)
        bad_json = "invalid-json"

        batch = [
            ("msg-fail-db", json.dumps(invalid_payload)),
            ("msg-bad-json", bad_json),
        ]

        with patch(
            "app.workers.event_worker.async_session_factory",
            MockSessionFactory(test_session),
        ):
            await process_batch(mock_redis, batch)

        # Verify no events created in DB
        db_events = (
            await test_session.execute(
                select(Event).where(Event.id == uuid.UUID(invalid_payload["id"]))
            )
        ).scalar_one_or_none()
        assert db_events is None

        # Verify failure routing to events:failed stream
        assert len(mock_redis.messages) == 2
        streams = [m[0] for m in mock_redis.messages]
        assert all(s == "events:failed" for s in streams)

        # Verify message IDs are acknowledged
        assert "msg-fail-db" in mock_redis.acked
        assert "msg-bad-json" in mock_redis.acked
