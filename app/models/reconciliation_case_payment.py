from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.reconciliation_case import ReconciliationCase


class ReconciliationCasePayment(Base):
    __tablename__ = "reconciliation_case_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    case_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("reconciliation_cases.case_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    payment_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("payments.payment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("case_id", "payment_id", name="uq_reconciliation_case_payment"),
    )

    reconciliation_case: Mapped["ReconciliationCase"] = relationship(
        "ReconciliationCase",
        back_populates="case_payments",
    )

    payment: Mapped["Payment"] = relationship("Payment")

