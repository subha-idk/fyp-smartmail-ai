"""LLM Service — handles generating personalized marketing emails using the Gemini API."""

import json
import logging
import os
import re
from datetime import UTC, datetime
from uuid import UUID

import google.generativeai as genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.product import Product
from app.models.user_profile import UserProfile
from app.models.user import User

logger = logging.getLogger(__name__)


class LLMService:
    """Service to generate marketing emails using Google Generative AI (Gemini)."""

    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        # Configure Gemini API
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)

    def _clean_json_response(self, raw_text: str) -> dict:
        """Strips markdown fences first, then extracts and parses the outermost JSON object."""
        text = raw_text.strip()
        
        # Strip markdown code fences first (e.g. ```json ... ``` or ``` ... ``` anywhere in response)
        text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
        text = text.strip()
        
        # Locate outermost { and }
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            text = text[start_idx:end_idx+1]
        else:
            raise ValueError("No valid JSON outer braces found in response.")
            
        return json.loads(text)

    async def generate_email(
        self,
        user: UserProfile,
        product: Product | None,
        email_type: str,
        email_log_id: UUID | None = None,
    ) -> dict:
        """Generates a marketing email using Gemini, falling back to static prompt template on error."""
        # 1. Resolve general variables
        user_name = "Customer"
        if self.db:
            # Query user to avoid lazy loading issues
            user_stmt = select(User).where(User.id == user.user_id)
            res = await self.db.execute(user_stmt)
            user_obj = res.scalar_one_or_none()
            if user_obj and user_obj.name:
                user_name = user_obj.name
        elif hasattr(user, "user") and user.user and hasattr(user.user, "name") and user.user.name:
            user_name = user.user.name

        product_name = product.name if product else "our featured products"
        product_price = f"{product.price:.2f}" if product else "0.00"
        
        preferred_category = "items"
        if user.preferred_categories and len(user.preferred_categories) > 0:
            preferred_category = user.preferred_categories[0]
        elif product and product.category:
            preferred_category = product.category

        # 2. Resolve type-specific variables
        days_inactive = 60
        if user.last_active_at:
            days_inactive = max(1, (datetime.now(UTC) - user.last_active_at).days)
        discount_offer = "15% Off"  # default retention discount

        # Chronological reconstruction of the active cart for abandoned_cart
        cart_items = "items in your cart"
        hours_since_abandoned = 24
        if email_type == "abandoned_cart" and self.db:
            from app.models.event import Event
            from app.models.product import Product as DBProduct
            
            event_stmt = select(Event).where(
                Event.user_id == user.user_id,
                Event.event_type.in_(["cart_add", "cart_remove", "purchase"])
            ).order_by(Event.timestamp.asc())
            event_res = await self.db.execute(event_stmt)
            events = event_res.scalars().all()
            
            cart_product_ids = set()
            last_cart_add_time = None
            for e in events:
                if e.event_type == "cart_add":
                    if e.product_id:
                        cart_product_ids.add(e.product_id)
                        last_cart_add_time = e.timestamp
                elif e.event_type == "cart_remove":
                    if e.product_id and e.product_id in cart_product_ids:
                        cart_product_ids.remove(e.product_id)
                elif e.event_type == "purchase":
                    cart_product_ids.clear()
            
            if cart_product_ids:
                prod_stmt = select(DBProduct.name).where(DBProduct.id.in_(list(cart_product_ids)))
                prod_res = await self.db.execute(prod_stmt)
                names = prod_res.scalars().all()
                if names:
                    cart_items = ", ".join(names)
            if last_cart_add_time:
                time_diff = datetime.now(UTC) - last_cart_add_time
                hours_since_abandoned = max(1, int(time_diff.total_seconds() // 3600))

        user_tier = "Bronze"
        spend = float(user.total_spend or 0.0)
        if spend >= 500.0:
            user_tier = "Gold"
        elif spend >= 200.0:
            user_tier = "Silver"
        total_spend = f"{spend:.2f}"

        # 3. Attempt Gemini generation
        try:
            # Read prompt template
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            template_path = os.path.join(base_dir, "prompts", f"{email_type}.txt")
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"Template not found: {template_path}")
                
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            variables = {
                "user_name": user_name,
                "product_name": product_name,
                "product_price": product_price,
                "preferred_category": preferred_category,
                "days_inactive": days_inactive,
                "discount_offer": discount_offer,
                "cart_items": cart_items,
                "hours_since_abandoned": hours_since_abandoned,
                "user_tier": user_tier,
                "total_spend": total_spend,
            }
            prompt = template_content.format(**variables)

            system_instruction = (
                "You are an expert email copywriter for an e-commerce brand. "
                "Write a concise, personalized marketing email. "
                "Return ONLY valid JSON with keys: subject (string), "
                "html_body (valid HTML string), plain_body (string). "
                "No markdown fences, no preamble."
            )

            # Invoke model
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            
            # Extract metrics
            tokens_used = response.usage_metadata.total_token_count if response.usage_metadata else 0
            
            # Clean and parse JSON
            result = self._clean_json_response(response.text)
            subject = result.get("subject", "Special update from SmartMail")
            html_body = result.get("html_body", "")
            plain_body = result.get("plain_body", "")
            
            if not html_body or not plain_body:
                raise ValueError("JSON response missing html_body or plain_body")

            # Log tokens_used to EmailLog if session is provided
            if self.db:
                from app.models.email_log import EmailLog
                if email_log_id:
                    stmt = select(EmailLog).where(EmailLog.id == email_log_id)
                    res = await self.db.execute(stmt)
                    log_record = res.scalar_one_or_none()
                    if log_record:
                        log_record.subject = subject
                        log_record.tokens_used = tokens_used
                        await self.db.flush()
                else:
                    log_record = EmailLog(
                        user_id=user.user_id,
                        email_type=email_type,
                        subject=subject,
                        tokens_used=tokens_used,
                        status="generated"
                    )
                    self.db.add(log_record)
                    await self.db.flush()

            return {
                "subject": subject,
                "html_body": html_body,
                "plain_body": plain_body,
                "tokens_used": tokens_used
            }

        except Exception as e:
            logger.error(f"Gemini API generation failed for {email_type}: {e}. Falling back to static template.")
            # Fallback path
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                template_path = os.path.join(base_dir, "prompts", f"{email_type}.txt")
                if os.path.exists(template_path):
                    with open(template_path, "r", encoding="utf-8") as f:
                        template_content = f.read()
                else:
                    template_content = "Subject: Special update from SmartMail\n\nHi {user_name},\n\nWe have a special recommendation for you: {product_name} for only ${product_price}."

                variables = {
                    "user_name": user_name,
                    "product_name": product_name,
                    "product_price": product_price,
                    "preferred_category": preferred_category,
                    "days_inactive": days_inactive,
                    "discount_offer": discount_offer,
                    "cart_items": cart_items,
                    "hours_since_abandoned": hours_since_abandoned,
                    "user_tier": user_tier,
                    "total_spend": total_spend,
                }
                rendered = template_content.format(**variables)

                subject = "Special update from SmartMail"
                plain_body = rendered
                lines = rendered.splitlines()
                if lines and lines[0].startswith("Subject:"):
                    subject = lines[0].replace("Subject:", "").strip()
                    plain_body = "\n".join(lines[1:]).strip()

                html_body = f"<html><body>{plain_body.replace('\n', '<br>')}</body></html>"

                # Log to db if session is provided
                if self.db:
                    from app.models.email_log import EmailLog
                    if email_log_id:
                        stmt = select(EmailLog).where(EmailLog.id == email_log_id)
                        res = await self.db.execute(stmt)
                        log_record = res.scalar_one_or_none()
                        if log_record:
                            log_record.subject = subject
                            log_record.tokens_used = 0
                            await self.db.flush()
                    else:
                        log_record = EmailLog(
                            user_id=user.user_id,
                            email_type=email_type,
                            subject=subject,
                            tokens_used=0,
                            status="generated"
                        )
                        self.db.add(log_record)
                        await self.db.flush()

                return {
                    "subject": subject,
                    "html_body": html_body,
                    "plain_body": plain_body,
                    "tokens_used": 0
                }
            except Exception as fallback_err:
                logger.error(f"Fallback rendering failed: {fallback_err}")
                return {
                    "subject": "Special offer from SmartMail",
                    "html_body": f"<html><body>Check out our special recommendations for {user_name}!</body></html>",
                    "plain_body": f"Check out our special recommendations for {user_name}!",
                    "tokens_used": 0
                }
