from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Adjustment(Base):
    __tablename__ = "adjustments"

    adjustment_id: Mapped[str] = mapped_column(
        String(50), primary_key=True
    )
    related_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )