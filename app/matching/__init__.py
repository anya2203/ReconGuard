"""ReconGuard Deterministic Matching Package."""

from app.matching.aggregation_matcher import AggregationMatcher
from app.matching.duplicate_detector import DuplicateDetector
from app.matching.engine import ReconciliationEngine
from app.matching.exact_matcher import ExactMatcher
from app.matching.fuzzy_matcher import FuzzyMatcher
from app.matching.types import (
    AggregationEvidence,
    AggregationMatchResult,
    ConfidenceBand,
    DuplicateClassification,
    DuplicateDetectionResult,
    DuplicateEvidence,
    ExactMatchEvidence,
    FuzzyMatchEvidence,
    MatchMethod,
    MatchResult,
    MatchStatus,
)

__all__ = [
    "ReconciliationEngine",
    "ExactMatcher",
    "FuzzyMatcher",
    "DuplicateDetector",
    "AggregationMatcher",
    "ExactMatchEvidence",
    "FuzzyMatchEvidence",
    "DuplicateEvidence",
    "DuplicateDetectionResult",
    "AggregationEvidence",
    "AggregationMatchResult",
    "MatchMethod",
    "MatchResult",
    "MatchStatus",
    "ConfidenceBand",
    "DuplicateClassification",
]





