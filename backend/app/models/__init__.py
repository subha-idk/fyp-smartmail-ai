"""ORM models package — import all models so Alembic can discover them."""

from app.models.user import User
from app.models.product import Product
from app.models.event import Event
from app.models.user_profile import UserProfile
from app.models.email_campaign import EmailCampaign
from app.models.email_log import EmailLog
from app.models.model_log import ModelLog

__all__ = [
    "User",
    "Product",
    "Event",
    "UserProfile",
    "EmailCampaign",
    "EmailLog",
    "ModelLog",
]
