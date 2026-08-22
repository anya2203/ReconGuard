from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id: Mapped[str] = mapped_column(
        String(50), primary_key=True
    )
    order_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("orders.order_id"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    tax_lines_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    