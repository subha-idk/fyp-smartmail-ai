"""EmailCampaign model — matches ``email_campaigns`` table in CONTEXT.md Section 3."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmailCampaign(Base):
    __tablename__ = "email_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # retention, abandoned_cart, recommendation, upsell, review_request
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        server_default="now()",
    )

    # Relationships
    email_logs = relationship(
        "EmailLog", back_populates="campaign", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<EmailCampaign {self.name}>"
