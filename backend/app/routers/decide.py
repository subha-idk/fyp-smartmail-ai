"""Decision API router — implements POST /api/decide/{user_id}."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import check_rate_limit, get_db, get_redis, verify_api_key
from app.models.user import User
from app.services.decision_service import DecisionService

router = APIRouter(prefix="/api/decide", tags=["decision"])


@router.post(
    "/{user_id}",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def decide_user_campaign(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
):
    """Evaluates campaign decisions for the given user."""
    # Verify user exists
    user_stmt = select(User).where(User.id == user_id)
    res = await db.execute(user_stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    decision_service = DecisionService(redis_client=redis)
    try:
        result = await decision_service.decide_email_type(db, user_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decision evaluation failed: {e}",
        )
