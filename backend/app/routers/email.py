import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import check_rate_limit, get_db, get_redis, verify_api_key, verify_presenter_passcode
from app.models.email_log import EmailLog
from app.models.user import User
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/send-email", tags=["Email Delivery"])


@router.post(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit), Depends(verify_presenter_passcode)],
)
async def send_email(
    user_id: UUID,
    bypass_cooldown: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Triggers the complete email decisioning, generation, and delivery pipeline for a user."""
    email_service = EmailService()
    try:
        if bypass_cooldown:
            await redis.delete(f"cooldown:{user_id}")
            logger.info("Bypassed cooldown for user %s by deleting cooldown key", user_id)

        result = await email_service.trigger_email_pipeline(db, redis, user_id)
        if result.get("status") == "skipped":
            # Cooldown check skipped, return skipped response
            return result
        return result
    except ValueError as val_err:
        logger.warning("User validation failed in send-email endpoint: %s", val_err)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        )
    except Exception as e:
        logger.error("Failed to execute send-email pipeline for user %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email dispatch pipeline failed: {e}",
        )
from pydantic import BaseModel

class SchedulerTogglePayload(BaseModel):
    enabled: bool

@router.post(
    "/scheduler/toggle",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit), Depends(verify_presenter_passcode)],
)
async def toggle_scheduler(
    payload: SchedulerTogglePayload,
    redis=Depends(get_redis),
):
    """Enables or disables the automatic background campaign email trigger job."""
    val = "true" if payload.enabled else "false"
    await redis.set("scheduler:autotrigger:enabled", val)
    return {"status": "success", "scheduler_autotrigger_enabled": payload.enabled}

@router.get(
    "/scheduler/status",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def get_scheduler_status(
    redis=Depends(get_redis),
):
    """Gets the current status of the background email trigger scheduler."""
    val = await redis.get("scheduler:autotrigger:enabled")
    return {"scheduler_autotrigger_enabled": val == "true"}


router_logs = APIRouter(prefix="/api/email_logs", tags=["Email Logs"])


@router_logs.get(
    "",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def get_email_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves paginated email logs joined with user names and emails."""
    offset = (page - 1) * limit

    # Count query
    count_stmt = select(func.count(EmailLog.id))
    total = (await db.execute(count_stmt)).scalar() or 0

    # Data query
    stmt = (
        select(EmailLog, User.name, User.email)
        .join(User, EmailLog.user_id == User.id)
        .order_by(EmailLog.sent_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    logs_list = []
    for log, name, email in rows:
        logs_list.append(
            {
                "id": str(log.id),
                "user_id": str(log.user_id),
                "user_name": name,
                "user_email": email,
                "email_type": log.email_type,
                "subject": log.subject,
                "status": log.status,
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
                "opened_at": log.opened_at.isoformat() if log.opened_at else None,
                "clicked_at": log.clicked_at.isoformat() if log.clicked_at else None,
                "tokens_used": log.tokens_used or 0,
            }
        )

    return {
        "logs": logs_list,
        "total": total,
    }

