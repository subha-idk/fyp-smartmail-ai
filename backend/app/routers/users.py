"""Users and user profiles router — implements Section 4 and 9 of CONTEXT.md."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import check_rate_limit, get_db, verify_api_key, verify_presenter_passcode
from app.models.user import User
from app.models.user_profile import UserProfile
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get(
    "",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Lists users with pagination and optional search query filter."""
    offset = (page - 1) * limit

    # Count query
    count_stmt = select(func.count(User.id))
    if q:
        count_stmt = count_stmt.where(
            or_(
                User.email.ilike(f"%{q}%"),
                User.name.ilike(f"%{q}%"),
            )
        )
    total = (await db.execute(count_stmt)).scalar() or 0

    # Data query
    query_stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    if q:
        query_stmt = query_stmt.where(
            or_(
                User.email.ilike(f"%{q}%"),
                User.name.ilike(f"%{q}%"),
            )
        )
    result = await db.execute(query_stmt)
    users = result.scalars().all()

    # Form response payload
    user_list = []
    for u in users:
        profile_data = None
        if u.profile:
            profile_data = {
                "total_events": u.profile.total_events,
                "total_purchases": u.profile.total_purchases,
                "total_spend": float(u.profile.total_spend),
                "last_active_at": u.profile.last_active_at.isoformat() if u.profile.last_active_at else None,
                "engagement_score": float(u.profile.engagement_score) if u.profile.engagement_score is not None else None,
                "churn_risk": float(u.profile.churn_risk) if u.profile.churn_risk is not None else None,
                "purchase_probability": float(u.profile.purchase_probability) if u.profile.purchase_probability is not None else None,
            }
        user_list.append(
            {
                "id": str(u.id),
                "email": u.email,
                "name": u.name,
                "country": u.country,
                "created_at": u.created_at.isoformat(),
                "profile": profile_data,
            }
        )

    return {
        "users": user_list,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get(
    "/{id}/profile",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def get_user_profile(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves or builds the analytical user profile."""
    # First assert user exists
    user_stmt = select(User).where(User.id == id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Find UserProfile
    profile_stmt = select(UserProfile).where(UserProfile.user_id == id)
    result = await db.execute(profile_stmt)
    profile = result.scalar_one_or_none()

    # If it does not exist, compute and create it on the fly
    if not profile:
        analytics_service = AnalyticsService()
        try:
            profile = await analytics_service.build_user_profile(db, id)
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate user profile on the fly: {e}",
            )

    return {
        "user_id": str(profile.user_id),
        "total_events": profile.total_events,
        "total_purchases": profile.total_purchases,
        "total_spend": float(profile.total_spend),
        "last_active_at": profile.last_active_at.isoformat() if profile.last_active_at else None,
        "days_since_last_purchase": profile.days_since_last_purchase,
        "preferred_categories": profile.preferred_categories or [],
        "top_viewed_products": [str(p_id) for p_id in profile.top_viewed_products] if profile.top_viewed_products else [],
        "engagement_score": float(profile.engagement_score) if profile.engagement_score is not None else None,
        "churn_risk": float(profile.churn_risk) if profile.churn_risk is not None else None,
        "purchase_probability": float(profile.purchase_probability) if profile.purchase_probability is not None else None,
        "rfm_recency": profile.rfm_recency,
        "rfm_frequency": profile.rfm_frequency,
        "rfm_monetary": float(profile.rfm_monetary) if profile.rfm_monetary is not None else None,
        "updated_at": profile.updated_at.isoformat(),
    }


from pydantic import BaseModel

class DemoSettingsPayload(BaseModel):
    email: str
    name: str

@router.put(
    "/{id}/email",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit), Depends(verify_presenter_passcode)],
)
async def update_user_email(
    id: uuid.UUID,
    payload: DemoSettingsPayload,
    db: AsyncSession = Depends(get_db),
):
    """Updates the email address and name of a user for demo purposes."""
    stmt = select(User).where(User.id == id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user.email = payload.email
    user.name = payload.name
    await db.commit()
    return {"status": "success", "email": user.email, "name": user.name}

