"""Scheduler service — configures and runs recurring background jobs using APScheduler."""

import logging
from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import async_session_factory
from app.models.user import User
from app.services.analytics_service import AnalyticsService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")


async def refresh_analytics_job() -> None:
    """Scheduled job to rebuild all user profiles."""
    logger.info("Starting scheduled analytics refresh...")
    analytics_service = AnalyticsService()

    async with async_session_factory() as session:
        try:
            result = await session.execute(select(User.id))
            user_ids = result.scalars().all()
            logger.info("Found %d users to refresh profiles", len(user_ids))
        except Exception as e:
            logger.error("Failed to query user IDs for analytics job: %s", e)
            return

        for user_id in user_ids:
            try:
                # Rebuild profile
                await analytics_service.build_user_profile(session, user_id)
                # Commit incrementally to release locks
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error("Error rebuilding profile for user %s: %s", user_id, e)

    logger.info("Completed scheduled analytics refresh job.")


async def ml_prediction_refresh_job() -> None:
    """Scheduled job to run inference for all users hourly."""
    logger.info("Starting scheduled ML prediction refresh...")
    from app.services.ml_service import MLService
    ml_service = MLService()

    async with async_session_factory() as session:
        try:
            result = await session.execute(select(User.id))
            user_ids = result.scalars().all()
            logger.info("Found %d users to run ML predictions", len(user_ids))
        except Exception as e:
            logger.error("Failed to query user IDs for ML prediction job: %s", e)
            return

        for user_id in user_ids:
            try:
                await ml_service.run_full_prediction(session, user_id)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error("Error running prediction for user %s: %s", user_id, e)

    logger.info("Completed scheduled ML prediction refresh job.")


async def weekly_retrain_job() -> None:
    """Scheduled job to rebuild features and retrain both models weekly."""
    logger.info("Starting weekly ML retraining job...")

    # 1. Rebuild features
    try:
        from ml.feature_pipeline import get_features_df
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ml_dir = os.path.join(base_dir, "ml")

        async with async_session_factory() as session:
            df = await get_features_df(session)
            if df.empty:
                logger.warning("No users found to build features.")
                return

            # Save features to CSV
            churn_path = os.path.join(ml_dir, "churn_features.csv")
            intent_path = os.path.join(ml_dir, "intent_features.csv")
            df.to_csv(churn_path, index=False)
            df.to_csv(intent_path, index=False)
            logger.info("Features rebuilt successfully.")
    except Exception as e:
        logger.error("Failed to rebuild features during weekly retrain: %s", e)
        return

    # 2. Retrain models
    try:
        from ml.train_churn import train_churn
        from ml.train_intent import train_intent

        logger.info("Retraining Churn model...")
        await train_churn()

        logger.info("Retraining Intent model...")
        await train_intent()

        logger.info("Weekly ML retraining job completed successfully.")
    except Exception as e:
        logger.error("Failed weekly ML retraining job: %s", e)


async def campaign_trigger_job() -> None:
    """Scheduled job to check and trigger emails for eligible users (up to 50)."""
    import redis.asyncio as aioredis
    
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        enabled = await redis_client.get("scheduler:autotrigger:enabled")
        if enabled != "true":
            logger.info("Scheduled campaign trigger job skipped: automatic email dispatch is DISABLED.")
            return
    except Exception as e:
        logger.error("Failed to check scheduler status in Redis: %s. Skipping job for safety.", e)
        return
    finally:
        await redis_client.close()

    logger.info("Starting scheduled campaign trigger job...")
    
    # 1. Calculate time thresholds
    now = datetime.now(UTC)
    active_threshold = now - timedelta(days=90)
    cooldown_threshold = now - timedelta(hours=settings.EMAIL_COOLDOWN_HOURS)
    
    from app.models.user_profile import UserProfile
    from app.models.email_log import EmailLog
    from app.services.email_service import EmailService
    import redis.asyncio as aioredis

    async with async_session_factory() as session:
        # Build query: select user_id from UserProfile where last_active_at >= active_threshold
        # AND user_id NOT IN (select user_id from EmailLog where sent_at >= cooldown_threshold)
        # Limit 50
        cooldown_subq = (
            select(EmailLog.user_id)
            .where(EmailLog.sent_at >= cooldown_threshold)
            .scalar_subquery()
        )
        
        query = (
            select(UserProfile.user_id)
            .where(UserProfile.last_active_at >= active_threshold)
            .where(UserProfile.user_id.notin_(cooldown_subq))
            .limit(50)
        )
        
        try:
            result = await session.execute(query)
            user_ids = result.scalars().all()
            logger.info("Found %d eligible users to trigger campaign emails", len(user_ids))
        except Exception as e:
            logger.error("Failed to query eligible users for campaign trigger job: %s", e)
            return

        if not user_ids:
            return

        # Prepare redis client
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        email_service = EmailService(redis_client=redis_client)
        
        try:
            for user_id in user_ids:
                try:
                    result = await email_service.trigger_email_pipeline(
                        session=session,
                        redis=redis_client,
                        user_id=user_id
                    )
                    logger.info("Triggered email for user %s: %s", user_id, result)
                except Exception as user_err:
                    logger.error("Error triggering email pipeline for user %s: %s", user_id, user_err)
        finally:
            await redis_client.close()
            
    logger.info("Completed scheduled campaign trigger job.")


async def start_scheduler() -> AsyncIOScheduler:
    """Configures, schedules, and starts the background job scheduler."""
    scheduler = AsyncIOScheduler()

    # Register the analytics refresh job to run every 15 minutes
    scheduler.add_job(
        refresh_analytics_job,
        "interval",
        minutes=15,
        id="refresh_analytics",
        replace_existing=True,
    )

    # Register the campaign trigger job to run every 30 minutes
    scheduler.add_job(
        campaign_trigger_job,
        "interval",
        minutes=30,
        id="campaign_trigger",
        replace_existing=True,
    )

    # Register the ML prediction refresh job to run every hour
    scheduler.add_job(
        ml_prediction_refresh_job,
        "interval",
        hours=1,
        id="ml_prediction_refresh",
        replace_existing=True,
    )

    # Register the weekly retrain job to run on Sundays at 02:00 UTC
    scheduler.add_job(
        weekly_retrain_job,
        "cron",
        day_of_week="sun",
        hour=2,
        minute=0,
        timezone="UTC",
        id="weekly_retrain",
        replace_existing=True,
    )

    logger.info("Starting APScheduler...")
    scheduler.start()
    return scheduler


async def shutdown_scheduler(scheduler: AsyncIOScheduler) -> None:
    """Stops the scheduler and waits for any running jobs to finish."""
    if scheduler and scheduler.running:
        logger.info("Shutting down APScheduler...")
        scheduler.shutdown(wait=True)
