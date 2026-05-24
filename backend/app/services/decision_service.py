"""Decision Service — implements the rule-based decision engine to prioritize marketing email types."""

import logging
from uuid import UUID
from datetime import datetime, UTC, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.config import settings
from app.models.user_profile import UserProfile
from app.models.event import Event
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


class DecisionService:
    """Service to evaluate marketing email campaigns for users based on historical activity and predictions."""

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.redis = redis_client
        self.analytics_service = AnalyticsService()

    async def _get_redis(self) -> aioredis.Redis:
        if self.redis is not None:
            return self.redis
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis

    async def check_cooldown(self, user_id: UUID) -> bool:
        """Checks if a user is in the email cooldown period."""
        redis = await self._get_redis()
        try:
            exists = await redis.exists(f"cooldown:{user_id}")
            return bool(exists)
        except Exception as e:
            logger.error("Failed to check cooldown: %s", e)
            return False

    async def set_cooldown(self, user_id: UUID) -> None:
        """Sets the cooldown period for a user after sending an email."""
        redis = await self._get_redis()
        try:
            await redis.setex(
                f"cooldown:{user_id}",
                settings.EMAIL_COOLDOWN_HOURS * 3600,
                "1"
            )
        except Exception as e:
            logger.error("Failed to set cooldown: %s", e)

    async def decide_email_type(self, session: AsyncSession, user_id: UUID) -> dict:
        """Evaluates rules in priority order to choose the best email campaign type for a user."""
        # 1. Cooldown active -> skip
        if await self.check_cooldown(user_id):
            return {
                "email_type": None,
                "rationale": "Email cooldown is active",
                "cooldown_active": True,
                "skip_reason": "cooldown_active"
            }

        decision = await self._evaluate_campaign_rules(session, user_id)
        if decision["email_type"] is not None:
            await self.set_cooldown(user_id)
        return decision

    async def _evaluate_campaign_rules(self, session: AsyncSession, user_id: UUID) -> dict:
        # Fetch profile
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        res = await session.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            profile = await self.analytics_service.build_user_profile(session, user_id)

        # 2. churn_risk > CHURN_RISK_THRESHOLD -> retention
        if profile.churn_risk is not None and float(profile.churn_risk) > settings.CHURN_RISK_THRESHOLD:
            return {
                "email_type": "retention",
                "rationale": f"churn_risk={float(profile.churn_risk):.4f} exceeds threshold {settings.CHURN_RISK_THRESHOLD}",
                "cooldown_active": False,
                "skip_reason": None
            }

        # 3. Cart items + last cart_add > CART_ABANDON_HOURS hours ago + no purchase since -> abandoned_cart
        event_stmt = select(Event).where(
            Event.user_id == user_id,
            Event.event_type.in_(["cart_add", "cart_remove", "purchase"])
        ).order_by(Event.timestamp.asc())
        event_res = await session.execute(event_stmt)
        events = event_res.scalars().all()

        cart = set()
        last_cart_add_time = None
        last_purchase_time = None

        for e in events:
            if e.event_type == "cart_add":
                if e.product_id:
                    cart.add(e.product_id)
                    last_cart_add_time = e.timestamp
            elif e.event_type == "cart_remove":
                if e.product_id and e.product_id in cart:
                    cart.remove(e.product_id)
            elif e.event_type == "purchase":
                cart.clear()
                last_purchase_time = e.timestamp

        now = datetime.now(UTC)
        if cart and last_cart_add_time:
            time_since_add = now - last_cart_add_time
            if time_since_add > timedelta(hours=settings.CART_ABANDON_HOURS):
                if not last_purchase_time or last_purchase_time < last_cart_add_time:
                    return {
                        "email_type": "abandoned_cart",
                        "rationale": f"Abandoned cart items detected with last add {last_cart_add_time.isoformat()} (>{settings.CART_ABANDON_HOURS}h ago)",
                        "cooldown_active": False,
                        "skip_reason": None
                    }

        # 4. purchase_probability > PURCHASE_PROB_THRESHOLD -> recommendation
        if profile.purchase_probability is not None and float(profile.purchase_probability) > settings.PURCHASE_PROB_THRESHOLD:
            return {
                "email_type": "recommendation",
                "rationale": f"purchase_probability={float(profile.purchase_probability):.4f} exceeds threshold {settings.PURCHASE_PROB_THRESHOLD}",
                "cooldown_active": False,
                "skip_reason": None
            }

        # 5. total_spend > TOP_SPENDER_THRESHOLD -> upsell
        if profile.total_spend is not None and float(profile.total_spend) > settings.TOP_SPENDER_THRESHOLD:
            return {
                "email_type": "upsell",
                "rationale": f"total_spend={float(profile.total_spend):.2f} exceeds threshold {settings.TOP_SPENDER_THRESHOLD}",
                "cooldown_active": False,
                "skip_reason": None
            }

        # 6. Last purchase was 7-14 days ago -> review_request
        if profile.days_since_last_purchase is not None and 7 <= profile.days_since_last_purchase <= 14:
            return {
                "email_type": "review_request",
                "rationale": f"Last purchase was {profile.days_since_last_purchase} days ago (within 7-14 days window)",
                "cooldown_active": False,
                "skip_reason": None
            }

        # 7. Default -> recommendation
        return {
            "email_type": "recommendation",
            "rationale": "Default recommendation campaign",
            "cooldown_active": False,
            "skip_reason": None
        }
