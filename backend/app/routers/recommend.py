"""Recommendation API router — implements GET /api/recommend/{user_id}."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import check_rate_limit, get_db, get_redis, verify_api_key
from app.models.user import User
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/recommend", tags=["Recommendations"])


@router.get(
    "/{user_id}",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def recommend_products(
    user_id: uuid.UUID,
    n: int = Query(3, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
):
    """Retrieves top-N recommended products for a user using collaborative filtering and cold start fallbacks."""
    # Verify user exists
    user_stmt = select(User).where(User.id == user_id)
    res = await db.execute(user_stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    rec_service = RecommendationService(redis_client=redis)
    try:
        products = await rec_service.get_recommendations(db, user_id, n)
        # Commit to save any updates/materialized profiles that occurred during recommendation building
        await db.commit()
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "category": p.category,
                "price": float(p.price),
                "stock": p.stock,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat(),
            }
            for p in products
        ]
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {e}",
        )
