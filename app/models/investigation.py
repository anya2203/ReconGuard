from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Investigation(Base):
    __tablename__ = "investigations"

    investigation_id: Mapped[str] = mapped_column(
        String(50), primary_key=True
    )

    case_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("reconciliation_cases.case_id"),
        nullable=False,
        index=True,
    )

    evidence_ids_json: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )

    cause: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    confidence: Mapped[float] = mapped_column(
        Float, nullable=False
    )

    recommended_action: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    requires_human: Mapped[bool] = mapped_column(
        nullable=False, default=True
    )

    raw_llm_output_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )