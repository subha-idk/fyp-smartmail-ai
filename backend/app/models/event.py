"""Event model — matches ``events`` table in CONTEXT.md Section 3."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Event(Base):
    __tablename__ = "events"

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
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # product_view, search, cart_add, cart_remove, purchase, email_open, email_click
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
    timestamp: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default="now()",
    )

    # Relationships
    user = relationship("User", back_populates="events")
    product = relationship("Product", back_populates="events")

    # Indexes as defined in CONTEXT.md
    __table_args__ = (
        Index("ix_events_user_id_timestamp", "user_id", timestamp.desc()),
        Index("ix_events_event_type_timestamp", "event_type", timestamp.desc()),
    )

    def __repr__(self) -> str:
        return f"<Event {self.event_type} user={self.user_id}>"
