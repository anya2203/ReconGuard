"""Pydantic schemas for the Audit Trail & Financial Control Evidence API."""

from typing import Any
from pydantic import BaseModel, Field


class AuditEventResponse(BaseModel):
    """Individual immutable audit event record in the exception lifecycle."""

    audit_id: str = Field(..., description="Unique audit event identifier")
    case_id: str = Field(..., description="Associated reconciliation case identifier")
    actor: str = Field(..., description="System or operational actor that triggered the event")
    action: str = Field(..., description="Action or event type identifier")
    source: str = Field(..., description="Category of event: DETERMINISTIC, AI, or HUMAN")
    details_json: dict[str, Any] = Field(default_factory=dict, description="Structured event context and evidence payload")
    timestamp: str = Field(..., description="ISO 8601 creation timestamp")


class CaseAuditTrailResponse(BaseModel):
    """Chronological audit trail for a specific reconciliation case."""

    case_id: str = Field(..., description="Reconciliation case identifier")
    order_id: str = Field(..., description="Associated order identifier")
    total_events: int = Field(..., description="Total number of chronological audit events")
    events: list[AuditEventResponse] = Field(..., description="Ordered list of audit events from creation to current state")

