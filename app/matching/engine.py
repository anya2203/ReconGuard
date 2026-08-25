"""Master Reconciliation Engine for ReconGuard.

Orchestrates deterministic matching components in a strict, explainable precedence:
1. Multi-Order Aggregation Matcher (resolves batch payouts)
2. Duplicate Payment Detector (resolves duplicates and flags retry ambiguities)
3. Exact Matcher (resolves clean 1:1 transactions)
4. Fuzzy Matcher (resolves micro-variances and reference typos)
5. Exception Classification (unmatched, discrepancies, active adjustments)

Operates exclusively on operational data with ZERO ground-truth leakage.
"""

import csv
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.matching.aggregation_matcher import AggregationMatcher
from app.matching.duplicate_detector import DuplicateDetector
from app.matching.exact_matcher import ExactMatcher
from app.matching.fuzzy_matcher import FuzzyMatcher
from app.matching.types import (
    ConfidenceBand,
    DuplicateClassification,
    MatchMethod,
    MatchResult,
    MatchStatus,
)


class ReconciliationEngine:
    """Master deterministic reconciliation engine orchestrating all matching components."""

    def __init__(
        self,
        orders: list[dict[str, Any]],
        payments: list[dict[str, Any]],
        settlements: list[dict[str, Any]],
        invoices: list[dict[str, Any]],
        adjustments: list[dict[str, Any]] | None = None,
    ):
        self.orders = {o["order_id"]: o for o in orders}
        self.payments = payments
        self.settlements = settlements
        self.invoices = invoices
        self.adjustments = adjustments or []

        # Initialize component engines
        self.aggregation_matcher = AggregationMatcher(
            settlements=self.settlements,
            payments=self.payments,
            orders=orders,
            invoices=self.invoices,
            adjustments=self.adjustments,
        )

        self.duplicate_detector = DuplicateDetector(
            payments=self.payments,
            orders=orders,
        )

        self.exact_matcher = ExactMatcher(
            orders=orders,
            payments=self.payments,
            settlements=self.settlements,
            invoices=self.invoices,
            adjustments=self.adjustments,
        )

        self.fuzzy_matcher = FuzzyMatcher(
            orders=orders,
            payments=self.payments,
            settlements=self.settlements,
            invoices=self.invoices,
            adjustments=self.adjustments,
        )

        # Precompute aggregation map for O(1) order lookup
        self._aggregation_order_map = self.aggregation_matcher.build_order_aggregation_map()

    @classmethod
    def from_csv_directory(cls, data_dir: Path | str) -> "ReconciliationEngine":
        """Load operational datasets from CSV files in data_dir without reading ground truth."""
        dir_path = Path(data_dir)
        gen_dir = dir_path / "generated" if (dir_path / "generated").exists() else dir_path

        def load_csv(filename: str) -> list[dict[str, Any]]:
            filepath = gen_dir / filename
            if not filepath.exists():
                return []
            with open(filepath, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)

        orders = load_csv("orders.csv")
        payments = load_csv("payments.csv")
        settlements = load_csv("settlements.csv")
        invoices = load_csv("invoices.csv")
        adjustments = load_csv("adjustments.csv")

        return cls(
            orders=orders,
            payments=payments,
            settlements=settlements,
            invoices=invoices,
            adjustments=adjustments,
        )

    def reconcile_order(self, order_id: str) -> MatchResult:
        """Execute deterministic reconciliation pipeline for a single order."""
        # 1. Multi-Order Settlement Aggregation Precedence
        if order_id in self._aggregation_order_map:
            return self._aggregation_order_map[order_id]

        # 2. Duplicate / Multi-Payment Evaluation
        dup_res = self.duplicate_detector.detect_duplicates_for_order(order_id)
        if dup_res.classification == DuplicateClassification.DUPLICATE:
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.DUPLICATE if hasattr(MatchStatus, "DUPLICATE") else MatchStatus.AMBIGUOUS,
                match_method=MatchMethod.DUPLICATE,
                payment_ids=[dup_res.primary_payment_id] + dup_res.duplicate_payment_ids if dup_res.primary_payment_id else dup_res.duplicate_payment_ids,
                confidence=dup_res.confidence,
                confidence_band=ConfidenceBand.HIGH.value,
                financial_impact=0.0,
                reason=dup_res.reason,
            )

        if dup_res.classification == DuplicateClassification.AMBIGUOUS:
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.AMBIGUOUS,
                match_method=MatchMethod.NONE,
                payment_ids=[dup_res.primary_payment_id] + dup_res.duplicate_payment_ids if dup_res.primary_payment_id else dup_res.duplicate_payment_ids,
                confidence=dup_res.confidence,
                confidence_band=ConfidenceBand.LOW.value,
                financial_impact=float(self.orders.get(order_id, {}).get("amount", 0.0)),
                reason=dup_res.reason,
            )

        # 3. Exact 1:1 Matching Precedence
        exact_res = self.exact_matcher.match_order(order_id)
        if exact_res.status == MatchStatus.MATCHED:
            exact_res.confidence_band = ConfidenceBand.HIGH.value
            return exact_res

        # 4. Fuzzy Matching for Unresolved Candidates
        fuzzy_res = self.fuzzy_matcher.match_order(order_id)
        if fuzzy_res.status == MatchStatus.MATCHED and fuzzy_res.match_method == MatchMethod.FUZZY:
            return fuzzy_res

        # 5. Return Fallback Discrepancy / Unmatched Result
        # Preserve the most descriptive evidence produced by the pipeline
        return fuzzy_res if fuzzy_res.status != MatchStatus.UNMATCHED else exact_res

    def reconcile_all(self) -> list[MatchResult]:
        """Execute reconciliation across all orders in deterministic order."""
        sorted_order_ids = sorted(self.orders.keys())
        return [self.reconcile_order(oid) for oid in sorted_order_ids]

    def get_summary(self, results: list[MatchResult] | None = None) -> dict[str, Any]:
        """Generate breakdown statistics from master reconciliation results."""
        if results is None:
            results = self.reconcile_all()

        total = len(results)

        # Status counts
        matched = sum(1 for r in results if r.status == MatchStatus.MATCHED)
        ambiguous = sum(1 for r in results if r.status == MatchStatus.AMBIGUOUS)
        unmatched = sum(1 for r in results if r.status == MatchStatus.UNMATCHED)
        discrepancy = sum(1 for r in results if r.status == MatchStatus.DISCREPANCY)

        # Method breakdown for matched cases
        matched_exact = sum(
            1 for r in results if r.status == MatchStatus.MATCHED and r.match_method == MatchMethod.EXACT
        )
        matched_fuzzy = sum(
            1 for r in results if r.status == MatchStatus.MATCHED and r.match_method == MatchMethod.FUZZY
        )
        matched_aggregation = sum(
            1 for r in results if r.status == MatchStatus.MATCHED and r.match_method == MatchMethod.AGGREGATION
        )

        return {
            "total_processed": total,
            "matched": matched,
            "matched_percentage": round((matched / total) * 100, 2) if total else 0.0,
            "matched_breakdown": {
                "EXACT": matched_exact,
                "EXACT_percentage": round((matched_exact / total) * 100, 2) if total else 0.0,
                "FUZZY": matched_fuzzy,
                "FUZZY_percentage": round((matched_fuzzy / total) * 100, 2) if total else 0.0,
                "AGGREGATION": matched_aggregation,
                "AGGREGATION_percentage": round((matched_aggregation / total) * 100, 2) if total else 0.0,
            },
            "ambiguous": ambiguous,
            "ambiguous_percentage": round((ambiguous / total) * 100, 2) if total else 0.0,
            "unmatched": unmatched,
            "unmatched_percentage": round((unmatched / total) * 100, 2) if total else 0.0,
            "discrepancy": discrepancy,
            "discrepancy_percentage": round((discrepancy / total) * 100, 2) if total else 0.0,
        }

