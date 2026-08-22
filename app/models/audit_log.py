from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[str] = mapped_column(
        String(50), primary_key=True
    )

    case_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("reconciliation_cases.case_id"),
        nullable=False,
        index=True,
    )

    actor: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    details_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )