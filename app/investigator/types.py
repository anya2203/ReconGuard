"""Data types, enums, schemas, and result models for the ReconGuard AI Investigator."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.policy.types import ExceptionCase


class FindingTaxonomy(str, Enum):
    """Controlled finding taxonomy for the AI Investigator."""

    VERIFIED_ROUNDING_VARIANCE = "VERIFIED_ROUNDING_VARIANCE"
    VERIFIED_REFERENCE_TYPO = "VERIFIED_REFERENCE_TYPO"
    MISSING_INVOICE_CONFIRMED = "MISSING_INVOICE_CONFIRMED"
    INCONCLUSIVE = "INCONCLUSIVE"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"


class InvestigationStatus(str, Enum):
    """Execution status and failure categories of an AI investigation."""

    COMPLETED = "COMPLETED"
    INCONCLUSIVE = "INCONCLUSIVE"
    FAILED = "FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    ITERATION_LIMIT = "ITERATION_LIMIT"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    TIMEOUT = "TIMEOUT"


@dataclass
class ToolCallRecord:
    """Record of an individual tool call executed during an investigation."""

    tool_name: str
    arguments: dict[str, Any]
    result_summary: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result_summary": self.result_summary,
            "timestamp": self.timestamp,
        }


@dataclass
class InvestigationContext:
    """Read-only context provided to the AI Investigator for a case."""

    case_id: str
    order_id: str
    exception_type: str
    policy_decision: str
    priority: str
    financial_impact: float
    payment_ids: list[str] = field(default_factory=list)
    settlement_ids: list[str] = field(default_factory=list)
    invoice_id: str | None = None
    adjustment_ids: list[str] = field(default_factory=list)
    match_method: str = "NONE"
    match_confidence: float = 0.0
    existing_evidence: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    explanation: str = ""

    @classmethod
    def from_exception_case(cls, case: ExceptionCase) -> "InvestigationContext":
        """Construct context directly from an ExceptionCase instance."""
        return cls(
            case_id=case.case_id,
            order_id=case.order_id,
            exception_type=case.exception_type.value if hasattr(case.exception_type, "value") else str(case.exception_type),
            policy_decision=case.decision.value if hasattr(case.decision, "value") else str(case.decision),
            priority=case.priority.value if hasattr(case.priority, "value") else str(case.priority),
            financial_impact=case.financial_impact,
            payment_ids=list(case.payment_ids),
            settlement_ids=list(case.settlement_ids),
            invoice_id=case.invoice_id,
            adjustment_ids=list(case.adjustment_ids),
            match_method=case.match_method,
            match_confidence=case.match_confidence,
            existing_evidence=dict(case.evidence),
            reason=case.reason,
            explanation=case.explanation,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InvestigationResult:
    """Structured, typed finding and recommendation produced by the AI Investigator."""

    case_id: str
    order_id: str
    finding: FindingTaxonomy
    root_cause: str
    evidence: dict[str, Any]
    confidence: float
    recommendation: str
    requires_human_review: bool
    supporting_payment_ids: list[str] = field(default_factory=list)
    supporting_settlement_ids: list[str] = field(default_factory=list)
    supporting_invoice_id: str | None = None
    investigation_status: InvestigationStatus = InvestigationStatus.COMPLETED
    error_category: str | None = None
    failure_reason: str | None = None
    tool_trace: list[ToolCallRecord] = field(default_factory=list)
    provider_used: str = "mock"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "order_id": self.order_id,
            "finding": self.finding.value if hasattr(self.finding, "value") else str(self.finding),
            "root_cause": self.root_cause,
            "evidence": self.evidence,
            "confidence": round(self.confidence, 4),
            "recommendation": self.recommendation,
            "requires_human_review": self.requires_human_review,
            "supporting_payment_ids": self.supporting_payment_ids,
            "supporting_settlement_ids": self.supporting_settlement_ids,
            "supporting_invoice_id": self.supporting_invoice_id,
            "investigation_status": self.investigation_status.value if hasattr(self.investigation_status, "value") else str(self.investigation_status),
            "error_category": self.error_category,
            "failure_reason": self.failure_reason,
            "tool_trace": [t.to_dict() for t in self.tool_trace],
            "provider_used": self.provider_used,
            "created_at": self.created_at,
        }

