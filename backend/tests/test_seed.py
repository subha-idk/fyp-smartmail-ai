"""Tests for the seed script — verifies idempotency and correct counts."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.product import Product
from app.models.event import Event
from app.models.email_campaign import EmailCampaign
from app.models.email_log import EmailLog
from data.seed import (
    generate_users,
    generate_products,
    generate_events,
    generate_campaigns,
    generate_email_logs,
    _upsert_batch,
)


class TestSeedGenerators:
    """Tests for data generation functions (no DB required)."""

    def test_generate_users_count(self):
        """Should generate the correct number of users."""
        users = generate_users(200)
        assert len(users) == 200

    def test_generate_users_unique_emails(self):
        """All generated emails should be unique."""
        users = generate_users(200)
        emails = [u["email"] for u in users]
        assert len(set(emails)) == 200

    def test_generate_users_valid_countries(self):
        """All countries should be from the allowed set."""
        users = generate_users(200)
        valid = {"IN", "US", "UK", "AU", "SG"}
        for u in users:
            assert u["country"] in valid

    def test_generate_products_count(self):
        """Should generate the correct number of products."""
        products = generate_products(50)
        assert len(products) == 50

    def test_generate_products_valid_categories(self):
        """All categories should be from the allowed set."""
        products = generate_products(50)
        valid = {"electronics", "fashion", "home", "beauty", "sports"}
        for p in products:
            assert p["category"] in valid

    def test_generate_events_count(self):
        """Should generate the correct number of events."""
        import uuid

        user_ids = [uuid.uuid4() for _ in range(5)]
        product_ids = [uuid.uuid4() for _ in range(5)]
        events = generate_events(5000, user_ids, product_ids)
        assert len(events) == 5000

    def test_generate_events_weighted_distribution(self):
        """Event types should roughly follow the weighted distribution."""
        import uuid

        user_ids = [uuid.uuid4() for _ in range(5)]
        product_ids = [uuid.uuid4() for _ in range(5)]
        events = generate_events(10000, user_ids, product_ids)

        type_counts = {}
        for e in events:
            type_counts[e["event_type"]] = type_counts.get(e["event_type"], 0) + 1

        # Check approximate distribution (with tolerance)
        total = len(events)
        assert type_counts.get("product_view", 0) / total > 0.50  # target: 60%
        assert type_counts.get("search", 0) / total > 0.15  # target: 20%
        assert type_counts.get("purchase", 0) / total < 0.15  # target: 8%

    def test_generate_events_null_product_for_search(self):
        """Search and email_click events should have null product_id."""
        import uuid

        user_ids = [uuid.uuid4() for _ in range(5)]
        product_ids = [uuid.uuid4() for _ in range(5)]
        events = generate_events(1000, user_ids, product_ids)

        for e in events:
            if e["event_type"] in ("search", "email_click"):
                assert e["product_id"] is None

    def test_generate_campaigns_count(self):
        """Should generate the correct number of campaigns."""
        campaigns = generate_campaigns(30)
        assert len(campaigns) == 30

    def test_generate_email_logs_count(self):
        """Should generate the correct number of email logs."""
        import uuid

        user_ids = [uuid.uuid4() for _ in range(5)]
        campaign_ids = [uuid.uuid4() for _ in range(5)]
        logs = generate_email_logs(500, user_ids, campaign_ids)
        assert len(logs) == 500


class TestSeedIdempotency:
    """Tests that inserting seed data twice does not create duplicates."""

    async def test_users_idempotent(self, test_session: AsyncSession):
        """Running user insert twice should not duplicate records."""
        users = generate_users(10)

        count1 = await _upsert_batch(test_session, User, users)
        await test_session.commit()

        count2 = await _upsert_batch(test_session, User, users)
        await test_session.commit()

        # Second insert should insert 0 new records
        assert count2 == 0

        # Total should be exactly 10
        result = await test_session.execute(select(func.count(User.id)))
        total = result.scalar()
        # May have more from other tests, but at least 10
        assert total >= 10

    async def test_products_idempotent(self, test_session: AsyncSession):
        """Running product insert twice should not duplicate records."""
        products = generate_products(5)

        await _upsert_batch(test_session, Product, products)
        await test_session.commit()

        count2 = await _upsert_batch(test_session, Product, products)
        await test_session.commit()

        assert count2 == 0
