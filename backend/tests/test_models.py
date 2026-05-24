"""CRUD and constraint tests for all SQLAlchemy models."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.product import Product
from app.models.event import Event
from app.models.user_profile import UserProfile
from app.models.email_campaign import EmailCampaign
from app.models.email_log import EmailLog


# ── User CRUD ─────────────────────────────────────────────────────────────────


class TestUserModel:
    """Tests for the User model."""

    async def test_create_user(self, test_session: AsyncSession):
        """Can create a user with valid data."""
        user = User(
            email="crud_test@example.com",
            name="CRUD Test",
            country="US",
        )
        test_session.add(user)
        await test_session.flush()

        assert user.id is not None
        assert user.email == "crud_test@example.com"
        assert user.created_at is not None

    async def test_read_user(self, test_session: AsyncSession, seed_users):
        """Can read a previously created user."""
        user_id = seed_users[0].id
        result = await test_session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one()
        assert user.email == "testuser1@example.com"

    async def test_update_user(self, test_session: AsyncSession, seed_users):
        """Can update a user's name."""
        user = seed_users[0]
        user.name = "Updated Name"
        await test_session.flush()

        result = await test_session.execute(
            select(User).where(User.id == user.id)
        )
        updated = result.scalar_one()
        assert updated.name == "Updated Name"

    async def test_delete_user(self, test_session: AsyncSession):
        """Can delete a user."""
        user = User(email="deleteme@example.com", name="Delete Me")
        test_session.add(user)
        await test_session.flush()

        await test_session.delete(user)
        await test_session.flush()

        result = await test_session.execute(
            select(User).where(User.email == "deleteme@example.com")
        )
        assert result.scalar_one_or_none() is None

    async def test_unique_email_constraint(
        self, test_session: AsyncSession, seed_users
    ):
        """Duplicate email should raise IntegrityError."""
        duplicate = User(
            email="testuser1@example.com",  # already exists via seed
            name="Duplicate",
        )
        test_session.add(duplicate)
        with pytest.raises(IntegrityError):
            await test_session.flush()
        await test_session.rollback()


# ── Product CRUD ──────────────────────────────────────────────────────────────


class TestProductModel:
    """Tests for the Product model."""

    async def test_create_product(self, test_session: AsyncSession):
        """Can create a product with valid data."""
        product = Product(
            name="Test Widget",
            category="electronics",
            price=29.99,
            stock=100,
        )
        test_session.add(product)
        await test_session.flush()

        assert product.id is not None
        assert product.is_active is True

    async def test_read_product(self, test_session: AsyncSession, seed_products):
        """Can read a product."""
        result = await test_session.execute(
            select(Product).where(Product.id == seed_products[0].id)
        )
        product = result.scalar_one()
        assert product.name == "Test Product 1"
        assert product.category == "electronics"

    async def test_product_default_stock(self, test_session: AsyncSession):
        """Stock defaults to 0 when not specified."""
        product = Product(name="No Stock", category="home", price=10.0)
        test_session.add(product)
        await test_session.flush()
        # Python-level default is 0
        assert product.stock == 0


# ── Event CRUD ────────────────────────────────────────────────────────────────


class TestEventModel:
    """Tests for the Event model."""

    async def test_create_event(
        self, test_session: AsyncSession, seed_users, seed_products
    ):
        """Can create an event linked to a user and product."""
        event = Event(
            user_id=seed_users[0].id,
            event_type="product_view",
            product_id=seed_products[0].id,
            session_id="test-sess-new",
        )
        test_session.add(event)
        await test_session.flush()

        assert event.id is not None
        assert event.timestamp is not None

    async def test_event_requires_user(self, test_session: AsyncSession):
        """Event without valid user_id should fail."""
        event = Event(
            user_id=uuid.uuid4(),  # non-existent user
            event_type="product_view",
        )
        test_session.add(event)
        with pytest.raises(IntegrityError):
            await test_session.flush()
        await test_session.rollback()

    async def test_event_nullable_product(
        self, test_session: AsyncSession, seed_users
    ):
        """Search events can have null product_id."""
        event = Event(
            user_id=seed_users[0].id,
            event_type="search",
            product_id=None,
            category="electronics",
        )
        test_session.add(event)
        await test_session.flush()

        assert event.product_id is None

    async def test_read_events_for_user(
        self, test_session: AsyncSession, seed_events, seed_users
    ):
        """Can query events by user_id."""
        user_id = seed_users[0].id
        result = await test_session.execute(
            select(Event).where(Event.user_id == user_id)
        )
        events = result.scalars().all()
        assert len(events) >= 1
        assert all(e.user_id == user_id for e in events)


# ── UserProfile CRUD ──────────────────────────────────────────────────────────


class TestUserProfileModel:
    """Tests for the UserProfile model."""

    async def test_create_profile(
        self, test_session: AsyncSession, seed_users
    ):
        """Can create a user profile."""
        profile = UserProfile(
            user_id=seed_users[0].id,
            total_events=50,
            total_purchases=5,
            total_spend=250.00,
            engagement_score=72.50,
            churn_risk=0.3500,
            purchase_probability=0.6200,
            rfm_recency=10,
            rfm_frequency=5,
            rfm_monetary=250.00,
            preferred_categories=["electronics", "fashion"],
        )
        test_session.add(profile)
        await test_session.flush()

        assert profile.user_id == seed_users[0].id

    async def test_profile_fk_constraint(self, test_session: AsyncSession):
        """Profile with non-existent user_id should fail."""
        profile = UserProfile(
            user_id=uuid.uuid4(),
            total_events=0,
        )
        test_session.add(profile)
        with pytest.raises(IntegrityError):
            await test_session.flush()
        await test_session.rollback()


# ── EmailCampaign CRUD ────────────────────────────────────────────────────────


class TestEmailCampaignModel:
    """Tests for the EmailCampaign model."""

    async def test_create_campaign(self, test_session: AsyncSession):
        """Can create an email campaign."""
        campaign = EmailCampaign(
            name="Test Retention Campaign",
            type="retention",
        )
        test_session.add(campaign)
        await test_session.flush()

        assert campaign.id is not None
        assert campaign.type == "retention"

    async def test_read_campaign(self, test_session: AsyncSession):
        """Can read a campaign after creation."""
        campaign = EmailCampaign(name="Read Test", type="upsell")
        test_session.add(campaign)
        await test_session.flush()

        result = await test_session.execute(
            select(EmailCampaign).where(EmailCampaign.id == campaign.id)
        )
        found = result.scalar_one()
        assert found.name == "Read Test"


# ── EmailLog CRUD ─────────────────────────────────────────────────────────────


class TestEmailLogModel:
    """Tests for the EmailLog model."""

    async def test_create_email_log(
        self, test_session: AsyncSession, seed_users
    ):
        """Can create an email log."""
        campaign = EmailCampaign(name="Log Test Campaign", type="retention")
        test_session.add(campaign)
        await test_session.flush()

        log = EmailLog(
            user_id=seed_users[0].id,
            campaign_id=campaign.id,
            email_type="retention",
            subject="We miss you!",
            status="sent",
            open_token="unique-open-token-123",
            click_token="unique-click-token-123",
            tokens_used=350,
        )
        test_session.add(log)
        await test_session.flush()

        assert log.id is not None
        assert log.status == "sent"

    async def test_email_log_unique_tokens(
        self, test_session: AsyncSession, seed_users
    ):
        """Duplicate open_token should raise IntegrityError."""
        log1 = EmailLog(
            user_id=seed_users[0].id,
            email_type="retention",
            open_token="duplicate-token",
        )
        test_session.add(log1)
        await test_session.flush()

        log2 = EmailLog(
            user_id=seed_users[1].id,
            email_type="upsell",
            open_token="duplicate-token",  # same token
        )
        test_session.add(log2)
        with pytest.raises(IntegrityError):
            await test_session.flush()
        await test_session.rollback()

    async def test_email_log_fk_user(self, test_session: AsyncSession):
        """Email log with non-existent user_id should fail."""
        log = EmailLog(
            user_id=uuid.uuid4(),
            email_type="retention",
        )
        test_session.add(log)
        with pytest.raises(IntegrityError):
            await test_session.flush()
        await test_session.rollback()
