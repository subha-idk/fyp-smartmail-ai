"""SmartMail AI+ — Idempotent seed script.

Generates dummy data for development and testing:
- 200 users
- 50 products
- 5000 events (weighted distribution)
- 30 email campaigns
- 500 email logs

Uses INSERT ... ON CONFLICT DO NOTHING for idempotency.
Run: ``python -m data.seed`` from the backend/ directory.
"""

import asyncio
import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.models.user import User
from app.models.product import Product
from app.models.event import Event
from app.models.user_profile import UserProfile
from app.models.email_campaign import EmailCampaign
from app.models.email_log import EmailLog

# Deterministic seed for reproducibility
random.seed(42)

# ── Constants ─────────────────────────────────────────────────────────────────

COUNTRIES = ["IN", "US", "UK", "AU", "SG"]
CATEGORIES = ["electronics", "fashion", "home", "beauty", "sports"]

EVENT_TYPES_WEIGHTED = (
    ["product_view"] * 60
    + ["search"] * 20
    + ["cart_add"] * 10
    + ["purchase"] * 8
    + ["email_click"] * 2
)

CAMPAIGN_TYPES = [
    "retention",
    "abandoned_cart",
    "recommendation",
    "upsell",
    "review_request",
]

EMAIL_STATUSES_WEIGHTED = ["sent"] * 90 + ["opened"] * 7 + ["failed"] * 3

FIRST_NAMES = [
    "Aarav", "Aditi", "Aisha", "Akash", "Amit", "Ananya", "Arjun", "Bhavya",
    "Chandra", "Deepa", "Dev", "Diya", "Elena", "Emma", "Ethan", "Fatima",
    "Gaurav", "Grace", "Harsh", "Isha", "James", "Jasmine", "Karan", "Kavya",
    "Leo", "Lily", "Manish", "Maya", "Nadia", "Neha", "Oliver", "Priya",
    "Rahul", "Riya", "Rohan", "Sakura", "Sam", "Sara", "Tanvi", "Uma",
    "Varun", "Vivek", "Wei", "Xander", "Yash", "Zara", "Zoe", "Noah",
    "Liam", "Sophia",
]

LAST_NAMES = [
    "Agarwal", "Anderson", "Brown", "Chen", "Das", "Davis", "Garcia",
    "Gupta", "Hernandez", "Iyer", "Jain", "Johnson", "Kim", "Kumar",
    "Lee", "Mehta", "Miller", "Moore", "Nair", "Patel", "Rao", "Reddy",
    "Rodriguez", "Shah", "Sharma", "Singh", "Smith", "Taylor", "Thomas",
    "Verma", "Wang", "Williams", "Wilson", "Wong", "Wu", "Yang", "Zhang",
]

PRODUCT_NAMES = {
    "electronics": [
        "Wireless Headphones Pro", "Bluetooth Speaker X", "USB-C Hub Ultra",
        "Mechanical Keyboard RGB", "4K Webcam", "Noise Cancelling Earbuds",
        "Portable Charger 20K", "Smart Watch Fit", "Laptop Stand Ergo",
        "Gaming Mouse Precision",
    ],
    "fashion": [
        "Cotton Crew T-Shirt", "Slim Fit Jeans", "Canvas Sneakers",
        "Leather Belt Classic", "Wool Beanie", "Silk Scarf Print",
        "Denim Jacket Vintage", "Running Shorts Pro", "Linen Shirt Summer",
        "Crossbody Bag Mini",
    ],
    "home": [
        "Ceramic Mug Set", "Bamboo Cutting Board", "LED Desk Lamp",
        "Memory Foam Pillow", "Scented Candle Pack", "Kitchen Scale Digital",
        "Plant Pot Terracotta", "Throw Blanket Cozy", "Wall Clock Modern",
        "Stainless Water Bottle",
    ],
    "beauty": [
        "Vitamin C Serum", "Moisturizer SPF 30", "Lip Balm Trio",
        "Hair Oil Argan", "Face Mask Clay", "Sunscreen Sport SPF 50",
        "Eye Cream Anti-Aging", "Body Lotion Shea", "Nail Polish Set",
        "Perfume Mist Floral",
    ],
    "sports": [
        "Yoga Mat Premium", "Resistance Bands Set", "Jump Rope Speed",
        "Foam Roller Deep Tissue", "Gym Gloves Pro", "Water Bottle Sport 1L",
        "Ankle Weights 2kg", "Tennis Balls Pack", "Swim Goggles Anti-Fog",
        "Compression Socks Run",
    ],
}

CAMPAIGN_NAME_TEMPLATES = [
    "{month} {type} Campaign",
    "Q{quarter} {type} Blast",
    "Weekly {type} Digest",
    "{type} Re-engagement",
    "Flash {type} Push",
    "Seasonal {type} Drive",
]

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# ── Generators ────────────────────────────────────────────────────────────────

def _random_datetime(days_back: int) -> datetime:
    """Generate a random datetime within the last ``days_back`` days."""
    delta = timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return datetime.now(UTC) - delta


def generate_users(n: int = 200) -> list[dict]:
    """Generate ``n`` user records."""
    users = []
    for i in range(1, n + 1):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        users.append(
            {
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"user-{i}"),
                "email": f"user{i}@example.com",
                "name": f"{first} {last}",
                "country": random.choice(COUNTRIES),
                "created_at": _random_datetime(365),
                "updated_at": datetime.now(UTC),
            }
        )
    return users


def generate_products(n: int = 50) -> list[dict]:
    """Generate ``n`` product records."""
    products = []
    product_idx = 0
    for cat in CATEGORIES:
        for pname in PRODUCT_NAMES[cat]:
            product_idx += 1
            if product_idx > n:
                break
            products.append(
                {
                    "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"product-{product_idx}"),
                    "name": pname,
                    "category": cat,
                    "price": round(random.uniform(5.0, 500.0), 2),
                    "stock": random.randint(0, 500),
                    "is_active": True,
                    "created_at": _random_datetime(180),
                }
            )
        if product_idx > n:
            break
    return products


def generate_events(
    n: int, user_ids: list[uuid.UUID], product_ids: list[uuid.UUID]
) -> list[dict]:
    """Generate ``n`` event records with weighted event types."""
    events = []

    # Pre-assign last_active_days for each user to guarantee the distribution
    user_last_active_days = {}
    shuffled_users = list(user_ids)
    random.shuffle(shuffled_users)

    # 45 users (22.5%) have last active between 61 and 120 days ago (churned)
    for u in shuffled_users[:45]:
        user_last_active_days[u] = random.randint(61, 120)
    # The rest (155 users) have last active between 1 and 60 days ago
    for u in shuffled_users[45:]:
        user_last_active_days[u] = random.randint(1, 60)

    # Generate 1 anchor event for each user to lock in their last_active_at
    now = datetime.now(UTC)
    for i, u in enumerate(user_ids):
        last_days = user_last_active_days[u]
        event_type = random.choice(EVENT_TYPES_WEIGHTED)
        product_id = None
        if event_type not in ("search", "email_click", "email_open"):
            product_id = random.choice(product_ids)

        events.append(
            {
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"event-anchor-{i}"),
                "user_id": u,
                "event_type": event_type,
                "product_id": product_id,
                "session_id": f"sess-{random.randint(1000, 9999)}",
                "category": random.choice(CATEGORIES) if event_type == "search" else None,
                "metadata_": {},
                "timestamp": now - timedelta(
                    days=last_days,
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                ),
            }
        )

    # Generate the remaining events (n - len(user_ids))
    for i in range(n - len(user_ids)):
        u = random.choice(user_ids)
        last_days = user_last_active_days[u]

        # Ensure the event timestamp is older than or equal to the anchor event's days back
        event_days_back = last_days + random.randint(0, 180)

        event_type = random.choice(EVENT_TYPES_WEIGHTED)
        product_id = None
        if event_type not in ("search", "email_click", "email_open"):
            product_id = random.choice(product_ids)

        events.append(
            {
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"event-{i}"),
                "user_id": u,
                "event_type": event_type,
                "product_id": product_id,
                "session_id": f"sess-{random.randint(1000, 9999)}",
                "category": random.choice(CATEGORIES) if event_type == "search" else None,
                "metadata_": {},
                "timestamp": now - timedelta(
                    days=event_days_back,
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                ),
            }
        )
    return events


def generate_campaigns(n: int = 30) -> list[dict]:
    """Generate ``n`` email campaign records."""
    campaigns = []
    for i in range(n):
        ctype = random.choice(CAMPAIGN_TYPES)
        template = random.choice(CAMPAIGN_NAME_TEMPLATES)
        name = template.format(
            month=random.choice(MONTHS),
            type=ctype.replace("_", " ").title(),
            quarter=random.randint(1, 4),
        )
        campaigns.append(
            {
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"campaign-{i}"),
                "name": name,
                "type": ctype,
                "created_at": _random_datetime(60),
            }
        )
    return campaigns


def generate_email_logs(
    n: int,
    user_ids: list[uuid.UUID],
    campaign_ids: list[uuid.UUID],
) -> list[dict]:
    """Generate ``n`` email log records."""
    logs = []
    for i in range(n):
        status = random.choice(EMAIL_STATUSES_WEIGHTED)
        sent_at = _random_datetime(60)
        logs.append(
            {
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"email-log-{i}"),
                "user_id": random.choice(user_ids),
                "campaign_id": random.choice(campaign_ids),
                "email_type": random.choice(CAMPAIGN_TYPES),
                "subject": f"Check out our latest {random.choice(CATEGORIES)} picks!",
                "status": status,
                "open_token": uuid.uuid5(
                    uuid.NAMESPACE_DNS, f"open-token-{i}"
                ).hex,
                "click_token": uuid.uuid5(
                    uuid.NAMESPACE_DNS, f"click-token-{i}"
                ).hex,
                "sent_at": sent_at,
                "opened_at": (
                    sent_at + timedelta(hours=random.randint(1, 48))
                    if status == "opened"
                    else None
                ),
                "clicked_at": None,
                "tokens_used": random.randint(200, 800) if status != "failed" else None,
            }
        )
    return logs


# ── Database insertion (idempotent) ───────────────────────────────────────────

async def _upsert_batch(session: AsyncSession, model, records: list[dict]) -> int:
    """Insert records using ON CONFLICT DO NOTHING for idempotency.

    Returns the number of records inserted.
    """
    if not records:
        return 0

    # Use PostgreSQL-specific INSERT ... ON CONFLICT DO NOTHING
    stmt = pg_insert(model).values(records).on_conflict_do_nothing()
    result = await session.execute(stmt)
    return result.rowcount


async def seed_database() -> None:
    """Run the full seed pipeline."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Truncate tables to ensure fresh seed data runs correctly and updates distributions
        print("Truncating existing tables...")
        await session.execute(text(
            "TRUNCATE TABLE users, products, events, user_profiles, email_campaigns, email_logs CASCADE;"
        ))
        await session.commit()

        # Generate data
        print("Generating seed data...")
        users = generate_users(200)
        products = generate_products(50)

        # Add one real demo user (idempotent)
        demo_user_id = uuid.uuid5(uuid.NAMESPACE_DNS, "user-patrasuvodip258@gmail.com")
        demo_user = {
            "id": demo_user_id,
            "email": "patrasuvodip258@gmail.com",
            "name": "Suvodip Patra",
            "country": "IN",
            "created_at": datetime.now(UTC) - timedelta(days=95),
            "updated_at": datetime.now(UTC),
        }
        users.append(demo_user)

        # Exclude demo user from general random events generation
        other_user_ids = [u["id"] for u in users if u["id"] != demo_user_id]
        product_ids = [p["id"] for p in products]

        events = generate_events(5000, other_user_ids, product_ids)

        # Generate custom events for demo user
        demo_events = []
        now = datetime.now(UTC)

        # Products for product_views (electronics & fashion)
        elec_fashion_product_ids = [
            uuid.uuid5(uuid.NAMESPACE_DNS, f"product-{i}") for i in range(1, 21)
        ]
        # All products for cart_add / purchase
        all_product_ids = [
            uuid.uuid5(uuid.NAMESPACE_DNS, f"product-{i}") for i in range(1, 51)
        ]

        # 1. 5 purchase events, last one 35 days ago
        purchase_offsets = [80, 70, 60, 50, 35]
        for idx, offset in enumerate(purchase_offsets):
            prod_id = random.choice(all_product_ids)
            demo_events.append({
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"demo-event-purchase-{idx}"),
                "user_id": demo_user_id,
                "event_type": "purchase",
                "product_id": prod_id,
                "session_id": f"sess-demo-purchase-{idx}",
                "category": None,
                "metadata_": {},
                "timestamp": now - timedelta(days=offset, hours=random.randint(0, 23)),
            })

        # 2. 10 cart_add events:
        # 8 older than 10 days, 2 within last 10 days
        cart_add_offsets = [82, 72, 62, 52, 37, 25, 20, 15, 5, 2]
        for idx, offset in enumerate(cart_add_offsets):
            prod_id = random.choice(all_product_ids)
            demo_events.append({
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"demo-event-cart-{idx}"),
                "user_id": demo_user_id,
                "event_type": "cart_add",
                "product_id": prod_id,
                "session_id": f"sess-demo-cart-{idx}",
                "category": None,
                "metadata_": {},
                "timestamp": now - timedelta(days=offset, hours=random.randint(0, 23)),
            })

        # 3. 30 product_view events:
        # 20 older than 10 days, 10 within last 10 days
        # Across electronics and fashion categories
        view_offsets_older = [random.randint(11, 90) for _ in range(20)]
        view_offsets_recent = [random.randint(1, 9) for _ in range(10)]
        view_offsets = view_offsets_older + view_offsets_recent
        for idx, offset in enumerate(view_offsets):
            prod_id = random.choice(elec_fashion_product_ids)
            demo_events.append({
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"demo-event-view-{idx}"),
                "user_id": demo_user_id,
                "event_type": "product_view",
                "product_id": prod_id,
                "session_id": f"sess-demo-view-{idx}",
                "category": None,
                "metadata_": {},
                "timestamp": now - timedelta(days=offset, hours=random.randint(0, 23)),
            })

        # 4. 15 recent events within last 10 days:
        # We already have:
        # - 2 cart_add events (at 5 and 2 days ago)
        # - 10 product_view events (between 1 and 9 days ago)
        # That's 12 recent events. We need 3 more to make exactly 15 recent events.
        # Let's add 3 search events within last 10 days (e.g. 4, 3, 1 days ago)
        search_offsets = [4, 3, 1]
        for idx, offset in enumerate(search_offsets):
            demo_events.append({
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"demo-event-search-{idx}"),
                "user_id": demo_user_id,
                "event_type": "search",
                "product_id": None,
                "session_id": f"sess-demo-search-{idx}",
                "category": random.choice(["electronics", "fashion"]),
                "metadata_": {},
                "timestamp": now - timedelta(days=offset, hours=random.randint(0, 23)),
            })

        # Also need 12 search events older than 10 days to make exactly 15 searches (total 60 events)
        search_offsets_older = [random.randint(11, 90) for _ in range(12)]
        for idx, offset in enumerate(search_offsets_older):
            demo_events.append({
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"demo-event-search-older-{idx}"),
                "user_id": demo_user_id,
                "event_type": "search",
                "product_id": None,
                "session_id": f"sess-demo-search-older-{idx}",
                "category": random.choice(["electronics", "fashion"]),
                "metadata_": {},
                "timestamp": now - timedelta(days=offset, hours=random.randint(0, 23)),
            })

        events.extend(demo_events)
        user_ids = [u["id"] for u in users]
        campaigns = generate_campaigns(30)

        campaign_ids = [c["id"] for c in campaigns]
        email_logs = generate_email_logs(500, user_ids, campaign_ids)

        # Insert in dependency order
        print("Seeding users...")
        inserted = await _upsert_batch(session, User, users)
        print(f"  Users: {inserted} inserted (of {len(users)})")

        print("Seeding products...")
        inserted = await _upsert_batch(session, Product, products)
        print(f"  Products: {inserted} inserted (of {len(products)})")

        print("Seeding events...")
        # Batch events in chunks of 500 to avoid parameter limit
        total_events_inserted = 0
        chunk_size = 500
        for i in range(0, len(events), chunk_size):
            chunk = events[i : i + chunk_size]
            inserted = await _upsert_batch(session, Event, chunk)
            total_events_inserted += inserted
        print(f"  Events: {total_events_inserted} inserted (of {len(events)})")

        print("Seeding email campaigns...")
        inserted = await _upsert_batch(session, EmailCampaign, campaigns)
        print(f"  Campaigns: {inserted} inserted (of {len(campaigns)})")

        print("Seeding email logs...")
        total_logs_inserted = 0
        for i in range(0, len(email_logs), chunk_size):
            chunk = email_logs[i : i + chunk_size]
            inserted = await _upsert_batch(session, EmailLog, chunk)
            total_logs_inserted += inserted
        print(f"  Email logs: {total_logs_inserted} inserted (of {len(email_logs)})")

        await session.commit()
        print("\n[OK] Seed completed successfully!")

    await engine.dispose()


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(seed_database())
