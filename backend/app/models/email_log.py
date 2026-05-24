"""EmailLog model — matches ``email_logs`` table in CONTEXT.md Section 3."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_campaigns.id"),
        nullable=True,
    )
    email_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="sent", server_default="'sent'"
    )  # sent, opened, clicked, failed, bounced
    open_token: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    click_token: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    sent_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        server_default="now()",
    )
    opened_at: Mapped[datetime | None] = mapped_column(nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    user = relationship("User", back_populates="email_logs")
    campaign = relationship("EmailCampaign", back_populates="email_logs")

    def __repr__(self) -> str:
        return f"<EmailLog {self.email_type} to user={self.user_id}>"
