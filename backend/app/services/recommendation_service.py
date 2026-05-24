"""Recommendation Service — generates personalized product recommendations using Collaborative Filtering and popularity fallbacks."""

import json
import logging
from uuid import UUID
import numpy as np
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.config import settings
from app.models.event import Event
from app.models.product import Product
from app.models.user_profile import UserProfile

logger = logging.getLogger(__name__)

# Check for scikit-surprise availability
try:
    import surprise
    from surprise import Dataset, Reader, SVD
    SURPRISE_AVAILABLE = True
except ImportError:
    SURPRISE_AVAILABLE = False

if SURPRISE_AVAILABLE:
    logger.info("Recommendation Engine: surprise collaborative filtering backend active.")
else:
    logger.info("Recommendation Engine: TruncatedSVD collaborative filtering backend active.")


class RecommendationService:
    """Service handling e-commerce product recommendations with caching and cold start support."""

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.redis = redis_client

    async def _get_redis(self) -> aioredis.Redis:
        if self.redis is not None:
            return self.redis
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis

    async def get_cold_start_ids(
        self, session: AsyncSession, profile: UserProfile | None, n: int, exclude_ids: set[str]
    ) -> list[str]:
        """Returns popularity-based product recommendations.

        Falls back to preferred category first, then overall popular items.
        """
        recommended_ids = []

        # 1. Try preferred category first
        if profile and profile.preferred_categories:
            pref_category = profile.preferred_categories[0]
            stmt = (
                select(Product.id)
                .outerjoin(Event, Event.product_id == Product.id)
                .where(Product.is_active == True, Product.category == pref_category)
            )
            if exclude_ids:
                stmt = stmt.where(~Product.id.in_([UUID(pid) for pid in exclude_ids]))

            stmt = stmt.group_by(Product.id).order_by(func.count(Event.id).desc()).limit(n)
            res = await session.execute(stmt)
            pref_ids = [str(r) for r in res.scalars().all()]
            recommended_ids.extend(pref_ids)
            exclude_ids.update(pref_ids)

        # 2. Fallback to overall popular products if we need more
        if len(recommended_ids) < n:
            limit_needed = n - len(recommended_ids)
            stmt = (
                select(Product.id)
                .outerjoin(Event, Event.product_id == Product.id)
                .where(Product.is_active == True)
            )
            if exclude_ids:
                stmt = stmt.where(~Product.id.in_([UUID(pid) for pid in exclude_ids]))

            stmt = stmt.group_by(Product.id).order_by(func.count(Event.id).desc()).limit(limit_needed)
            res = await session.execute(stmt)
            overall_ids = [str(r) for r in res.scalars().all()]
            recommended_ids.extend(overall_ids)

        return recommended_ids[:n]

    async def get_recommendations(self, session: AsyncSession, user_id: UUID, n: int = 3) -> list[Product]:
        """Retrieves top-N recommended products for a user.

        Uses Redis caching (TTL 1h) with format recommend:{user_id}:{n}.
        """
        redis = await self._get_redis()
        cache_key = f"recommend:{user_id}:{n}"

        # 1. Try Cache Hit
        try:
            cached_val = await redis.get(cache_key)
            if cached_val:
                cached_ids = json.loads(cached_val)
                if cached_ids:
                    stmt = select(Product).where(Product.id.in_([UUID(pid) for pid in cached_ids]))
                    res = await session.execute(stmt)
                    products = res.scalars().all()
                    product_map = {p.id: p for p in products}
                    return [product_map[UUID(pid)] for pid in cached_ids if UUID(pid) in product_map]
        except Exception as e:
            logger.error("Failed reading recommendation cache: %s", e)

        # 2. Fetch User Profile
        profile_stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        profile_res = await session.execute(profile_stmt)
        profile = profile_res.scalar_one_or_none()

        total_events = profile.total_events if profile else 0

        # Define products user already purchased or carted to exclude
        ex_stmt = select(Event.product_id).where(
            Event.user_id == user_id,
            Event.event_type.in_(["purchase", "cart_add"]),
            Event.product_id.isnot(None),
        )
        ex_res = await session.execute(ex_stmt)
        exclude_ids = {str(pid) for pid in ex_res.scalars().all()}

        recommended_ids = []

        # 3. Check Cold-Start Threshold (< 5 events)
        if total_events < 5:
            recommended_ids = await self.get_cold_start_ids(session, profile, n, exclude_ids)
        else:
            # 4. Collaborative Filtering (CF)
            try:
                # Query interaction events
                events_stmt = select(Event).where(
                    Event.event_type.in_(["purchase", "cart_add", "product_view"]),
                    Event.product_id.isnot(None),
                )
                events_res = await session.execute(events_stmt)
                events = events_res.scalars().all()

                if not events:
                    # If database has no events, fallback to cold start
                    recommended_ids = await self.get_cold_start_ids(session, profile, n, exclude_ids)
                else:
                    data_dict = []
                    for e in events:
                        # Interaction scores: Purchase = 5.0, Cart Add = 3.0, View = 1.0
                        score = 1.0
                        if e.event_type == "purchase":
                            score = 5.0
                        elif e.event_type == "cart_add":
                            score = 3.0
                        data_dict.append({
                            "user_id": str(e.user_id),
                            "product_id": str(e.product_id),
                            "score": score,
                        })

                    df = pd.DataFrame(data_dict)
                    df_ratings = df.groupby(["user_id", "product_id"])["score"].sum().reset_index()

                    user_str = str(user_id)
                    prod_stmt = select(Product.id).where(Product.is_active == True)
                    prod_res = await session.execute(prod_stmt)
                    all_product_ids = [str(pid) for pid in prod_res.scalars().all()]
                    candidate_product_ids = [pid for pid in all_product_ids if pid not in exclude_ids]

                    if not candidate_product_ids:
                        recommended_ids = []
                    elif SURPRISE_AVAILABLE:
                        # Run scikit-surprise SVD
                        reader = Reader(rating_scale=(1.0, 100.0))
                        dataset = Dataset.load_from_df(df_ratings[["user_id", "product_id", "score"]], reader)
                        trainset = dataset.build_full_trainset()
                        algo = SVD(random_state=42)
                        algo.fit(trainset)

                        predictions = []
                        for pid in candidate_product_ids:
                            pred = algo.predict(user_str, pid)
                            predictions.append((pid, pred.est))

                        predictions.sort(key=lambda x: x[1], reverse=True)
                        recommended_ids = [pid for pid, _ in predictions[:n]]
                    else:
                        # Run sklearn TruncatedSVD fallback
                        user_item = df_ratings.pivot(index="user_id", columns="product_id", values="score").fillna(0.0)

                        if user_str in user_item.index:
                            from sklearn.decomposition import TruncatedSVD
                            n_components = min(10, user_item.shape[1] - 1, user_item.shape[0] - 1)
                            if n_components > 0:
                                svd = TruncatedSVD(n_components=n_components, random_state=42)
                                latent = svd.fit_transform(user_item)
                                reconst = np.dot(latent, svd.components_)
                                predictions_df = pd.DataFrame(reconst, index=user_item.index, columns=user_item.columns)

                                user_preds = predictions_df.loc[user_str]
                                candidate_preds = []
                                for pid in candidate_product_ids:
                                    score = user_preds.get(pid, 0.0)
                                    candidate_preds.append((pid, score))

                                candidate_preds.sort(key=lambda x: x[1], reverse=True)
                                recommended_ids = [pid for pid, _ in candidate_preds[:n]]
                            else:
                                recommended_ids = []
                        else:
                            recommended_ids = []

                    # Fill remainder if SVD predictions failed/insufficient
                    if len(recommended_ids) < n:
                        exclude_ids.update(recommended_ids)
                        fill_ids = await self.get_cold_start_ids(session, profile, n - len(recommended_ids), exclude_ids)
                        recommended_ids.extend(fill_ids)

            except Exception as e:
                logger.error("Collaborative filtering error, falling back: %s", e)
                # Fallback on exception
                recommended_ids = await self.get_cold_start_ids(session, profile, n, exclude_ids)

        # 5. Fetch Products
        if not recommended_ids:
            return []

        products_stmt = select(Product).where(Product.id.in_([UUID(pid) for pid in recommended_ids]))
        products_res = await session.execute(products_stmt)
        products = products_res.scalars().all()
        product_map = {p.id: p for p in products}

        ordered_products = [product_map[UUID(pid)] for pid in recommended_ids if UUID(pid) in product_map]

        # 6. Cache recommendations in Redis for 1 hour (3600s)
        try:
            serialized_ids = json.dumps([str(p.id) for p in ordered_products])
            await redis.setex(cache_key, 3600, serialized_ids)
        except Exception as e:
            logger.error("Failed writing recommendation cache: %s", e)

        return ordered_products
