"""UserProfile model — matches ``user_profiles`` table in CONTEXT.md Section 3.

This is a materialized profile rebuilt by the analytics engine.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import ARRAY, Integer, Numeric, String, Text, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        primary_key=True,
    )
    total_events: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0")
    )
    total_purchases: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0")
    )
    total_spend: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, server_default=text("0")
    )
    last_active_at: Mapped[datetime | None] = mapped_column(nullable=True)
    days_since_last_purchase: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    preferred_categories: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )  # ordered by frequency
    top_viewed_products: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )  # top 10
    engagement_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # 0–100
    churn_risk: Mapped[float | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )  # 0–1, from ML model
    purchase_probability: Mapped[float | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )  # 0–1, from ML model
    rfm_recency: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # days since last purchase
    rfm_frequency: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # number of purchases
    rfm_monetary: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )  # total spend
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        server_default=text("now()"),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile user={self.user_id}>"
