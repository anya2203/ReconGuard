from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Settlement(Base):
    __tablename__ = "settlements"

    settlement_id: Mapped[str] = mapped_column(
        String(50), primary_key=True
    )
    utr: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    fees: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    settled_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )