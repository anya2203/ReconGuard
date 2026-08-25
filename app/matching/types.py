"""Type definitions and schemas for the ReconGuard Matching Engine."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class MatchStatus(str, Enum):
    """Outcome status of the reconciliation matching process."""

    MATCHED = "MATCHED"
    AMBIGUOUS = "AMBIGUOUS"
    UNMATCHED = "UNMATCHED"
    DISCREPANCY = "DISCREPANCY"


class MatchMethod(str, Enum):
    """Method utilized to achieve the match verdict."""

    EXACT = "EXACT"
    FUZZY = "FUZZY"
    AGGREGATION = "AGGREGATION"
    DUPLICATE = "DUPLICATE"
    NONE = "NONE"


class ConfidenceBand(str, Enum):
    """Confidence categorization for matching decisions."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


@dataclass
class ExactMatchEvidence:
    """Structured, explainable evidence produced during exact matching."""

    order_id_verified: bool = False
    order_status: str | None = None
    order_amount: float | None = None

    payment_id: str | None = None
    payment_amount: float | None = None
    payment_status: str | None = None
    payment_method: str | None = None
    utr: str | None = None

    settlement_id: str | None = None
    settlement_amount: float | None = None
    settlement_fees: float | None = None
    settlement_expected_net: float | None = None
    settlement_date: str | None = None
    settlement_sla_breached: bool = False

    invoice_id: str | None = None
    invoice_amount: float | None = None

    adjustment_ids: list[str] = field(default_factory=list)
    adjustment_types: list[str] = field(default_factory=list)

    amount_difference: float = 0.0
    matched_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FuzzyMatchEvidence:
    """Structured, explainable evidence produced during fuzzy matching."""

    candidate_payment_id: str | None = None
    candidate_settlement_id: str | None = None

    amount_difference: float = 0.0
    amount_difference_percentage: float = 0.0

    date_difference_days: float = 0.0
    reference_similarity: float = 0.0

    # Component scores (0.0 to 1.0)
    amount_score: float = 0.0
    reference_score: float = 0.0
    date_score: float = 0.0
    relationship_score: float = 0.0

    final_score: float = 0.0
    confidence_band: str = "NONE"

    matched_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    top_candidates: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MatchResult:
    """Structured result returned by the matching engine for a case/order."""

    order_id: str
    status: MatchStatus
    match_method: MatchMethod
    payment_ids: list[str] = field(default_factory=list)
    settlement_ids: list[str] = field(default_factory=list)
    invoice_id: str | None = None
    adjustment_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    confidence_band: str = "NONE"
    financial_impact: float = 0.0
    evidence: ExactMatchEvidence | FuzzyMatchEvidence | dict[str, Any] = field(
        default_factory=ExactMatchEvidence
    )
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["status"] = self.status.value
        res["match_method"] = self.match_method.value
        return res


class DuplicateClassification(str, Enum):
    """Classification produced by the duplicate detector."""

    DUPLICATE = "DUPLICATE"
    AMBIGUOUS = "AMBIGUOUS"
    NO_DUPLICATE = "NO_DUPLICATE"


@dataclass
class DuplicateEvidence:
    """Structured evidence for a suspected pair of duplicate payments."""

    payment_id_1: str
    payment_id_2: str
    order_id_1: str
    order_id_2: str
    same_order: bool = False
    same_amount: bool = False
    amount_1: float = 0.0
    amount_2: float = 0.0
    amount_difference: float = 0.0
    same_utr: bool = False
    utr_1: str | None = None
    utr_2: str | None = None
    reference_similarity: float = 0.0
    timestamp_difference_seconds: float = 0.0
    same_payment_method: bool = False
    duplicate_score: float = 0.0
    classification: str = DuplicateClassification.NO_DUPLICATE.value
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DuplicateDetectionResult:
    """Result of duplicate evaluation for an order or payment group."""

    order_id: str | None = None
    classification: DuplicateClassification = DuplicateClassification.NO_DUPLICATE
    primary_payment_id: str | None = None
    duplicate_payment_ids: list[str] = field(default_factory=list)
    candidate_pairs: list[DuplicateEvidence] = field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["classification"] = self.classification.value
        return res


@dataclass
class AggregationEvidence:
    """Structured evidence for multi-order settlement batch reconciliation."""

    settlement_id: str
    settlement_utr: str
    settlement_amount: float
    settlement_fees: float
    expected_gross_amount: float
    payment_ids: list[str] = field(default_factory=list)
    order_ids: list[str] = field(default_factory=list)
    matched_payment_total: float = 0.0
    amount_difference: float = 0.0
    candidate_count: int = 0
    confidence_band: str = "HIGH"
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AggregationMatchResult:
    """Result of evaluating a settlement for multi-order aggregation."""

    settlement_id: str
    status: MatchStatus
    match_method: MatchMethod = MatchMethod.AGGREGATION
    payment_ids: list[str] = field(default_factory=list)
    order_ids: list[str] = field(default_factory=list)
    settlement_amount: float = 0.0
    settlement_fees: float = 0.0
    matched_payment_total: float = 0.0
    amount_difference: float = 0.0
    candidate_count: int = 0
    confidence: float = 0.0
    confidence_band: str = "NONE"
    evidence: AggregationEvidence | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["status"] = self.status.value
        res["match_method"] = self.match_method.value
        return res




