"""Email generation API router — implements POST /api/generate-email."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import check_rate_limit, get_db, get_redis, verify_api_key
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.product import Product
from app.services.llm_service import LLMService

router = APIRouter(prefix="/api/generate-email", tags=["LLM"])


class GenerateEmailPayload(BaseModel):
    user_id: uuid.UUID
    email_type: str
    product_id: uuid.UUID | None = None

    class Config:
        from_attributes = True


@router.post(
    "",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def generate_email_endpoint(
    payload: GenerateEmailPayload,
    db: AsyncSession = Depends(get_db),
):
    """Generates a marketing email for a user, custom-tailored using the Gemini LLM."""
    # 1. Verify user exists
    user_stmt = select(User).where(User.id == payload.user_id)
    res = await db.execute(user_stmt)
    user_obj = res.scalar_one_or_none()
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # 2. Get user profile (build if missing)
    profile_stmt = select(UserProfile).where(UserProfile.user_id == payload.user_id)
    res = await db.execute(profile_stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        from app.services.analytics_service import AnalyticsService
        analytics_service = AnalyticsService()
        profile = await analytics_service.build_user_profile(db, payload.user_id)

    # 3. Verify product exists if provided
    product = None
    if payload.product_id:
        product_stmt = select(Product).where(Product.id == payload.product_id)
        res = await db.execute(product_stmt)
        product = res.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )

    # 4. Generate email via LLMService
    llm_service = LLMService(db=db)
    try:
        result = await llm_service.generate_email(
            user=profile,
            product=product,
            email_type=payload.email_type
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email generation failed: {e}",
        )
