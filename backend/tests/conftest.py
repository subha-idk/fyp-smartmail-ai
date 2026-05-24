"""Shared test fixtures for SmartMail AI+ backend tests.

Provides:
- ``test_engine``: async engine pointing at the test database
- ``test_session``: async session with automatic rollback
- ``seed_users``, ``seed_products``, ``seed_events``: pre-loaded test data
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.database import Base

# Import all models so they register with metadata
from app.models import (  # noqa: F401
    User,
    Product,
    Event,
    UserProfile,
    EmailCampaign,
    EmailLog,
)


# ── Test database URL ─────────────────────────────────────────────────────────
# Appends '_test' to the database name to isolate tests
_base_url = settings.DATABASE_URL
if "_test" not in _base_url:
    _test_url = _base_url.rsplit("/", 1)[0] + "/" + _base_url.rsplit("/", 1)[1] + "_test"
else:
    _test_url = _base_url


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create and set up test database engine.

    Creates all tables before the session and drops them after.
    """
    # First, connect to default 'postgres' db to create the test database
    admin_url = _base_url.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    test_db_name = _test_url.rsplit("/", 1)[1]

    async with admin_engine.connect() as conn:
        # Check if test database exists
        result = await conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{test_db_name}'")
        )
        if not result.scalar():
            await conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))

    await admin_engine.dispose()

    # Create engine for test database
    engine = create_async_engine(_test_url, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after all tests complete
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional session that rolls back after each test."""
    # Clean tables first to ensure no cross-test leakage
    async with test_engine.begin() as conn:
        await conn.execute(text(
            "TRUNCATE TABLE users, products, events, user_profiles, email_campaigns, email_logs CASCADE;"
        ))

    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


# ── Seed data fixtures ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def seed_users(test_session: AsyncSession) -> list[User]:
    """Insert 5 test users and return them."""
    users = []
    for i in range(1, 6):
        user = User(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"test-user-{i}"),
            email=f"testuser{i}@example.com",
            name=f"Test User {i}",
            country=["IN", "US", "UK", "AU", "SG"][i - 1],
        )
        test_session.add(user)
        users.append(user)
    await test_session.flush()
    return users


@pytest_asyncio.fixture
async def seed_products(test_session: AsyncSession) -> list[Product]:
    """Insert 5 test products and return them."""
    products = []
    categories = ["electronics", "fashion", "home", "beauty", "sports"]
    for i in range(1, 6):
        product = Product(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"test-product-{i}"),
            name=f"Test Product {i}",
            category=categories[i - 1],
            price=round(10.0 * i, 2),
            stock=100,
        )
        test_session.add(product)
        products.append(product)
    await test_session.flush()
    return products


@pytest_asyncio.fixture
async def seed_events(
    test_session: AsyncSession,
    seed_users: list[User],
    seed_products: list[Product],
) -> list[Event]:
    """Insert 10 test events and return them."""
    event_types = [
        "product_view", "product_view", "search", "cart_add",
        "purchase", "product_view", "search", "cart_add",
        "email_click", "product_view",
    ]
    events = []
    for i, etype in enumerate(event_types):
        event = Event(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"test-event-{i}"),
            user_id=seed_users[i % len(seed_users)].id,
            event_type=etype,
            product_id=(
                seed_products[i % len(seed_products)].id
                if etype not in ("search", "email_click", "email_open")
                else None
            ),
            session_id=f"test-sess-{i}",
            timestamp=datetime.now(UTC) - timedelta(days=i),
        )
        test_session.add(event)
        events.append(event)
    await test_session.flush()
    return events
