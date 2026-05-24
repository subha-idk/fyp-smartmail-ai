"""Email Service — handles sending marketing emails, injecting tracking tokens, and managing the email send pipeline."""

import asyncio
import logging
import re
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.config import settings
from app.models.email_log import EmailLog
from app.models.user_profile import UserProfile
from app.models.user import User
from app.services.decision_service import DecisionService
from app.services.recommendation_service import RecommendationService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class EmailService:
    """Service to inject tracking links, dispatch emails via SMTP/SendGrid, and orchestrate the send pipeline."""

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.redis = redis_client

    async def _get_redis(self) -> aioredis.Redis:
        if self.redis is not None:
            return self.redis
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis

    def inject_tracking(self, html_body: str, open_token: str, click_token: str) -> str:
        """Injects a tracking pixel and replaces product links with tracked redirect links."""
        # 1. Inject open tracking pixel
        pixel = f'<img src="{settings.BACKEND_URL}/api/track/open/{open_token}" width="1" height="1" style="display:none" />'
        if "</body>" in html_body:
            html_body = re.sub(r"(</body>)", f"{pixel}\n\\1", html_body, flags=re.IGNORECASE)
        else:
            html_body = f"{html_body}\n{pixel}"

        # 2. Replace anchor links with redirect click tracking links
        def replace_anchor(match):
            anchor_text = match.group(0)
            href_match = re.search(r'href=["\']([^"\']+)["\']', anchor_text)
            if href_match:
                original_url = href_match.group(1)
                # Don't replace if it is a hash link or already tracked
                if original_url.startswith("#") or "/api/track/" in original_url:
                    return anchor_text
                new_url = f"{settings.BACKEND_URL}/api/track/click/{click_token}?redirect={original_url}"
                new_anchor = re.sub(
                    r'href=["\']([^"\']+)["\']',
                    f'href="{new_url}"',
                    anchor_text
                )
                return new_anchor
            return anchor_text

        return re.sub(r"<a\s+[^>]*>", replace_anchor, html_body, flags=re.IGNORECASE)

    async def send(self, to_email: str, subject: str, html_body: str, plain_body: str) -> None:
        """Sends an email using the configured email provider (SendGrid or SMTP)."""
        if settings.EMAIL_PROVIDER == "sendgrid":
            await self._send_sendgrid(to_email, subject, html_body, plain_body)
        else:
            await self._send_smtp(to_email, subject, html_body, plain_body)

    async def _send_sendgrid(self, to_email: str, subject: str, html_body: str, plain_body: str) -> None:
        """Dispatches email via SendGrid HTTP API (lazy loaded)."""
        # Lazy import sendgrid helper libraries
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email="noreply@smartmail.ai",
            to_emails=to_email,
            subject=subject,
            html_content=html_body,
            plain_text_content=plain_body
        )

        def _sync_send():
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            return sg.send(message)

        await asyncio.to_thread(_sync_send)

    async def _send_smtp(self, to_email: str, subject: str, html_body: str, plain_body: str) -> None:
        """Dispatches email via aiosmtplib to Zoho or local Mailhog."""
        import aiosmtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
        msg["To"] = to_email

        part1 = MIMEText(plain_body, "plain")
        part2 = MIMEText(html_body, "html")
        msg.attach(part1)
        msg.attach(part2)

        # Resolve credentials
        username = settings.SMTP_USERNAME if settings.SMTP_USERNAME else None
        password = settings.SMTP_PASSWORD if settings.SMTP_PASSWORD else None

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=username,
            password=password,
            use_tls=settings.SMTP_USE_SSL,
            start_tls=settings.SMTP_USE_TLS,
        )

    async def trigger_email_pipeline(
        self, session: AsyncSession, redis: aioredis.Redis, user_id: UUID
    ) -> dict:
        """Runs the full campaign decisioning, generation, tracking injection, and dispatch pipeline."""
        # 1. Fetch user to ensure existence
        user_stmt = select(User).where(User.id == user_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # 2. Run Decision Engine
        decision_service = DecisionService(redis_client=redis)
        decision = await decision_service.decide_email_type(session, user_id)

        # 3. Check for cooldown block
        if decision.get("cooldown_active"):
            return {"status": "skipped", "reason": "cooldown"}

        email_type = decision["email_type"]

        # 4. Fetch Recommendation
        recommendation_service = RecommendationService(redis_client=redis)
        recs = await recommendation_service.get_recommendations(session, user_id, n=1)
        product = recs[0] if recs else None

        # 5. Fetch or build User Profile
        profile_stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        profile_res = await session.execute(profile_stmt)
        profile = profile_res.scalar_one_or_none()
        if not profile:
            from app.services.analytics_service import AnalyticsService
            analytics_service = AnalyticsService()
            profile = await analytics_service.build_user_profile(session, user_id)

        # 6. Generate Tracking Tokens & Create EmailLog in 'sending' state
        open_token = str(uuid.uuid4())
        click_token = str(uuid.uuid4())

        email_log = EmailLog(
            user_id=user_id,
            email_type=email_type,
            status="sending",
            open_token=open_token,
            click_token=click_token,
            tokens_used=0,
        )
        session.add(email_log)
        await session.flush()

        # 7. Generate Personalized Email Content via LLM
        llm_service = LLMService(db=session)
        email_data = await llm_service.generate_email(
            user=profile,
            product=product,
            email_type=email_type,
            email_log_id=email_log.id
        )

        subject = email_data["subject"]
        html_body = email_data["html_body"]
        plain_body = email_data["plain_body"]

        # 8. Inject Tracking Pixel and Click Redirect URLs
        tracked_html = self.inject_tracking(html_body, open_token, click_token)

        # 9. Send and commit
        try:
            await self.send(
                to_email=user.email,
                subject=subject,
                html_body=tracked_html,
                plain_body=plain_body
            )
            email_log.status = "sent"
            await session.commit()

            # Ensure Redis Cooldown is set
            await decision_service.set_cooldown(user_id)

            return {
                "log_id": str(email_log.id),
                "status": "sent",
                "email_type": email_type,
                "subject": subject,
                "tokens_used": email_log.tokens_used
            }
        except Exception as e:
            logger.error(f"Failed to dispatch email to user {user_id}: {e}")
            email_log.status = "failed"
            await session.commit()

            # Remove cooldown on failed dispatch
            await redis.delete(f"cooldown:{user_id}")
            raise e
