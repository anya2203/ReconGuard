from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReconciliationCase(Base):
    __tablename__ = "reconciliation_cases"

    case_id: Mapped[str] = mapped_column(
        String(50), primary_key=True
    )

    order_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("orders.order_id"),
        nullable=True,
        index=True,
    )

    payment_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("payments.payment_id"),
        nullable=True,
        index=True,
    )

    settlement_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("settlements.settlement_id"),
        nullable=True,
        index=True,
    )

    invoice_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("invoices.invoice_id"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )

    confidence: Mapped[float] = mapped_column(
        Float, nullable=False
    )

    financial_impact: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )