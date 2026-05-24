"""Pydantic schemas for event tracking validation."""

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class EventPayload(BaseModel):
    user_id: uuid.UUID
    event_type: Literal[
        "product_view",
        "search",
        "cart_add",
        "cart_remove",
        "purchase",
        "email_open",
        "email_click",
    ]
    product_id: uuid.UUID | None = None
    session_id: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        from_attributes = True
