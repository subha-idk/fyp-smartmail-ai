"""Prediction API router — implements POST /api/predict/{user_id}."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import check_rate_limit, get_db, get_redis, verify_api_key
from app.models.user import User
from app.services.ml_service import MLService

router = APIRouter(prefix="/api/predict", tags=["ML"])


@router.post(
    "/{user_id}",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def predict_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
):
    """Triggers on-the-fly features extraction and prediction for user churn risk and purchase intent."""
    # Verify user exists
    user_stmt = select(User).where(User.id == user_id)
    res = await db.execute(user_stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    ml_service = MLService(redis_client=redis)
    try:
        result = await ml_service.run_full_prediction(db, user_id)
        # Commit changes to database since we updated the user profile risk probabilities
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference run failed: {e}",
        )
