from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.reconciliation_case import ReconciliationCase
    from app.models.settlement import Settlement


class ReconciliationCaseSettlement(Base):
    __tablename__ = "reconciliation_case_settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    case_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("reconciliation_cases.case_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    settlement_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("settlements.settlement_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("case_id", "settlement_id", name="uq_reconciliation_case_settlement"),
    )

    reconciliation_case: Mapped["ReconciliationCase"] = relationship(
        "ReconciliationCase",
        back_populates="case_settlements",
    )

    settlement: Mapped["Settlement"] = relationship("Settlement")

