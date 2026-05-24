"""ModelLog model — for logging model training metrics."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ModelLog(Base):
    __tablename__ = "model_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        server_default="now()",
    )

    def __repr__(self) -> str:
        return f"<ModelLog name={self.model_name} version={self.version}>"
