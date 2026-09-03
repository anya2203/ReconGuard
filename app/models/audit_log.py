from datetime import datetime, timezone
from typing import Any

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

    @property
    def source(self) -> str:
        """Categorize event source as DETERMINISTIC, AI, or HUMAN."""
        if self.details_json and "source" in self.details_json:
            return self.details_json["source"]
        if "AI" in self.actor.upper() or "AI" in self.action.upper():
            return "AI"
        if "HUMAN" in self.actor.upper() or "HUMAN" in self.action.upper() or "OPERATIONS" in self.actor.upper():
            return "HUMAN"
        return "DETERMINISTIC"

    def to_dict(self) -> dict[str, Any]:
        """Serialize audit log record to dictionary."""
        ts = self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp)
        return {
            "audit_id": self.audit_id,
            "case_id": self.case_id,
            "actor": self.actor,
            "action": self.action,
            "source": self.source,
            "details_json": dict(self.details_json) if self.details_json else {},
            "timestamp": ts,
        }