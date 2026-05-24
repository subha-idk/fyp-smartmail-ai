"""ML Service — handles loading ML models, executing predictions, and updating user profiles."""

import os
import glob
import re
from uuid import UUID
from datetime import datetime, UTC
import joblib
import pandas as pd
import redis.asyncio as aioredis

from app.config import settings
from app.models.user_profile import UserProfile
from app.services.analytics_service import AnalyticsService

# Define feature columns matching Section 5 of CONTEXT.md
FEATURE_COLS = [
    "days_since_last_active",
    "days_since_last_purchase",
    "total_events_7d",
    "total_events_30d",
    "total_purchases",
    "total_spend",
    "cart_add_count_30d",
    "purchase_count_30d",
    "engagement_score",
    "rfm_recency",
    "rfm_frequency",
    "rfm_monetary",
]

_cached_models = {
    "churn": {"model": None, "version": None},
    "intent": {"model": None, "version": None},
}


def get_latest_version_on_disk(model_name: str) -> str:
    """Checks the local ml/models directory to find the latest version string (e.g. v2)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    models_dir = os.path.join(base_dir, "ml", "models")
    files = glob.glob(os.path.join(models_dir, f"{model_name}_v*.pkl"))
    max_ver = 0
    for f in files:
        match = re.search(rf"{model_name}_v(\d+)\.pkl$", os.path.basename(f))
        if match:
            max_ver = max(max_ver, int(match.group(1)))
    if max_ver > 0:
        return f"v{max_ver}"
    return "v1"


def load_model_from_disk(model_name: str, version: str):
    """Loads a specific version of the pickle model from disk."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    model_path = os.path.join(base_dir, "ml", "models", f"{model_name}_{version}.pkl")
    if os.path.exists(model_path):
        try:
            return joblib.load(model_path)
        except Exception:
            return None
    return None


class MLService:
    """Service to predict churn risk and purchase intent for users."""

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.redis = redis_client
        self.analytics_service = AnalyticsService()

    async def _get_redis(self) -> aioredis.Redis:
        if self.redis is not None:
            return self.redis
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis

    async def get_model(self, model_name: str):
        """Fetches the active model version from Redis, checking the cache and reloading if updated."""
        redis = await self._get_redis()
        try:
            active_version = await redis.get(f"ml:active_model:{model_name}")
        except Exception:
            active_version = None

        if not active_version:
            active_version = get_latest_version_on_disk(model_name)
            try:
                await redis.set(f"ml:active_model:{model_name}", active_version)
            except Exception:
                pass

        cached = _cached_models[model_name]
        if cached["model"] is None or cached["version"] != active_version:
            model = load_model_from_disk(model_name, active_version)
            if model is not None:
                _cached_models[model_name] = {
                    "model": model,
                    "version": active_version,
                }
            else:
                # If active_version from Redis was not found, fallback to latest on disk
                latest_disk_ver = get_latest_version_on_disk(model_name)
                model = load_model_from_disk(model_name, latest_disk_ver)
                if model is not None:
                    _cached_models[model_name] = {
                        "model": model,
                        "version": latest_disk_ver,
                    }

        return _cached_models[model_name]["model"]

    async def predict_churn(self, features: dict) -> float:
        """Loads churn model and returns risk probability."""
        model = await self.get_model("churn")
        if model is None:
            return 0.0

        df = pd.DataFrame([features])[FEATURE_COLS]
        classes = model.classes_ if hasattr(model, "classes_") else model.named_steps["clf"].classes_
        if len(classes) > 1:
            prob = model.predict_proba(df)[0, 1]
        else:
            prob = float(model.predict(df)[0])
        return float(prob)

    async def predict_purchase_intent(self, features: dict) -> float:
        """Loads purchase intent model and returns purchase probability."""
        model = await self.get_model("intent")
        if model is None:
            return 0.0

        df = pd.DataFrame([features])[FEATURE_COLS]
        classes = model.classes_ if hasattr(model, "classes_") else model.named_steps["clf"].classes_
        if len(classes) > 1:
            prob = model.predict_proba(df)[0, 1]
        else:
            prob = float(model.predict(df)[0])
        return float(prob)

    async def run_full_prediction(self, session, user_id: UUID) -> dict:
        """Computes current feature vector, executes predictions, and updates user profile in database."""
        # 1. Build/fetch user profile analytical details
        profile = await self.analytics_service.build_user_profile(session, user_id)
        rolling = await self.analytics_service.get_rolling_event_counts(session, user_id)

        # 2. Construct feature vector
        now = datetime.now(UTC)
        last_active = profile.last_active_at
        days_since_last_active = (now - last_active).days if last_active else 365
        days_since_last_active = max(0, days_since_last_active)

        days_since_last_purchase = (
            profile.days_since_last_purchase
            if profile.days_since_last_purchase is not None
            else 365
        )
        rfm_recency = (
            profile.rfm_recency
            if profile.rfm_recency is not None
            else 365
        )

        features = {
            "days_since_last_active": int(days_since_last_active),
            "days_since_last_purchase": int(days_since_last_purchase),
            "total_events_7d": int(rolling["total_events_7d"]),
            "total_events_30d": int(rolling["total_events_30d"]),
            "total_purchases": int(profile.total_purchases),
            "total_spend": float(profile.total_spend or 0.0),
            "cart_add_count_30d": int(rolling["cart_add_count_30d"]),
            "purchase_count_30d": int(rolling["purchase_count_30d"]),
            "engagement_score": float(profile.engagement_score or 0.0),
            "rfm_recency": int(rfm_recency),
            "rfm_frequency": int(profile.rfm_frequency or 0),
            "rfm_monetary": float(profile.rfm_monetary or 0.0),
        }

        # 3. Predict churn risk and purchase probability
        churn_risk = await self.predict_churn(features)
        purchase_prob = await self.predict_purchase_intent(features)

        # 4. Save to UserProfile DB model
        profile.churn_risk = churn_risk
        profile.purchase_probability = purchase_prob
        profile.updated_at = datetime.now(UTC)

        await session.flush()

        return {
            "user_id": str(user_id),
            "churn_risk": round(churn_risk, 4),
            "purchase_probability": round(purchase_prob, 4),
        }
