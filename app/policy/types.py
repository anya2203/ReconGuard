"""Type definitions, enums, and data schemas for the ReconGuard Policy Engine."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class PolicyDecision(str, Enum):
    """Business decision produced by the deterministic policy layer."""

    AUTO_RESOLVE = "AUTO_RESOLVE"
    AI_INVESTIGATION = "AI_INVESTIGATION"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    ESCALATE = "ESCALATE"


class ExceptionType(str, Enum):
    """Specific category of exception identified for the case."""

    NONE = "NONE"
    ROUNDING_VARIANCE = "ROUNDING_VARIANCE"
    REFERENCE_MISMATCH = "REFERENCE_MISMATCH"
    MISSING_INVOICE = "MISSING_INVOICE"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    SLA_BREACH = "SLA_BREACH"
    MISSING_PAYMENT = "MISSING_PAYMENT"
    CHARGEBACK = "CHARGEBACK"
    REFUND = "REFUND"
    AMBIGUOUS_CANDIDATE = "AMBIGUOUS_CANDIDATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    MISSING_SETTLEMENT = "MISSING_SETTLEMENT"
    UNCLASSIFIED_DISCREPANCY = "UNCLASSIFIED_DISCREPANCY"


class CasePriority(str, Enum):
    """Operational priority / risk level assigned to an exception case."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class ExceptionCase:
    """Actionable exception case representing a policy decision on a reconciliation match result."""

    case_id: str
    order_id: str
    decision: PolicyDecision
    exception_type: ExceptionType
    priority: CasePriority
    financial_impact: float = 0.0
    payment_ids: list[str] = field(default_factory=list)
    settlement_ids: list[str] = field(default_factory=list)
    invoice_id: str | None = None
    adjustment_ids: list[str] = field(default_factory=list)
    match_method: str = "NONE"
    match_confidence: float = 0.0
    evidence: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    explanation: str = ""
    next_action: str = ""
    requires_ai: bool = False
    requires_human: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize case to a JSON-serializable dictionary."""
        return {
            "case_id": self.case_id,
            "order_id": self.order_id,
            "decision": self.decision.value,
            "exception_type": self.exception_type.value,
            "priority": self.priority.value,
            "financial_impact": round(self.financial_impact, 2),
            "payment_ids": list(self.payment_ids),
            "settlement_ids": list(self.settlement_ids),
            "invoice_id": self.invoice_id,
            "adjustment_ids": list(self.adjustment_ids),
            "match_method": self.match_method,
            "match_confidence": round(self.match_confidence, 4),
            "evidence": dict(self.evidence),
            "reason": self.reason,
            "explanation": self.explanation,
            "next_action": self.next_action,
            "requires_ai": self.requires_ai,
            "requires_human": self.requires_human,
            "created_at": self.created_at,
        }

