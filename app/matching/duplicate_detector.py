"""Deterministic Duplicate Detector for ReconGuard.

Identifies duplicate payments and distinguishes between:
1. Exact Duplicates: Same UTR / transaction identifier, same amount, replayed webhook or duplicate capture.
2. Ambiguous Retries: Same order/amount, different UTR references (candidate retry payments requiring escalation).
3. No Duplicate: Clean single payment transactions.

Operates exclusively on operational data with ZERO ground-truth leakage.
"""

import csv
import difflib
from datetime import datetime
from pathlib import Path
from typing import Any

from app.matching.types import (
    DuplicateClassification,
    DuplicateDetectionResult,
    DuplicateEvidence,
)

# Time thresholds in seconds
TIME_WINDOW_TIGHT_SECONDS = 60.0  # 1 minute
TIME_WINDOW_RETRY_SECONDS = 300.0  # 5 minutes
TIME_WINDOW_MAX_SECONDS = 86400.0  # 24 hours

# Weights for transparent duplicate scoring
WEIGHT_UTR = 0.40
WEIGHT_AMOUNT = 0.25
WEIGHT_ORDER = 0.20
WEIGHT_TIME = 0.15


class DuplicateDetector:
    """Deterministic duplicate payment detector with transparent pair scoring."""

    def __init__(
        self,
        payments: list[dict[str, Any]],
        orders: list[dict[str, Any]] | None = None,
    ):
        self.payments = payments
        self.orders = {o["order_id"]: o for o in orders} if orders else {}

        # Index payments by order_id
        self.payments_by_order: dict[str, list[dict[str, Any]]] = {}
        # Index payments by payment_id
        self.payments_by_id: dict[str, dict[str, Any]] = {}
        # Index payments by UTR
        self.payments_by_utr: dict[str, list[dict[str, Any]]] = {}

        for p in payments:
            pid = p.get("payment_id", "").strip()
            oid = p.get("order_id", "").strip()
            utr = p.get("utr", "").strip()

            if pid:
                self.payments_by_id[pid] = p
            if oid:
                self.payments_by_order.setdefault(oid, []).append(p)
            if utr:
                self.payments_by_utr.setdefault(utr, []).append(p)

    @classmethod
    def from_csv_directory(cls, data_dir: Path | str) -> "DuplicateDetector":
        """Load operational datasets from CSV files without reading ground truth."""
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

        return cls(payments=payments, orders=orders)

    def evaluate_pair(self, p1: dict[str, Any], p2: dict[str, Any]) -> DuplicateEvidence:
        """Evaluate a pair of suspicious payment records and produce explainable evidence."""
        pid1 = p1.get("payment_id", "")
        pid2 = p2.get("payment_id", "")
        oid1 = p1.get("order_id", "")
        oid2 = p2.get("order_id", "")
        utr1 = p1.get("utr", "").strip()
        utr2 = p2.get("utr", "").strip()
        method1 = p1.get("method", "")
        method2 = p2.get("method", "")

        amt1 = float(p1.get("amount", 0.0))
        amt2 = float(p2.get("amount", 0.0))
        amt_diff = round(abs(amt1 - amt2), 2)
        same_amt = amt_diff <= 0.001
        same_order = (oid1 == oid2) and bool(oid1)
        same_utr = (utr1 == utr2) and bool(utr1)
        same_method = (method1 == method2) and bool(method1)

        # UTR reference similarity
        if utr1 and utr2:
            ref_sim = round(difflib.SequenceMatcher(None, utr1, utr2).ratio(), 4)
        else:
            ref_sim = 0.0

        # Timestamp difference calculation
        try:
            t1 = datetime.fromisoformat(p1.get("created_at", ""))
            t2 = datetime.fromisoformat(p2.get("created_at", ""))
            time_diff_sec = round(abs((t2 - t1).total_seconds()), 2)
        except Exception:
            time_diff_sec = 999999.0

        # Time score calculation
        if time_diff_sec <= TIME_WINDOW_TIGHT_SECONDS:
            time_score = 1.0
        elif time_diff_sec <= TIME_WINDOW_RETRY_SECONDS:
            time_score = 0.8
        elif time_diff_sec <= TIME_WINDOW_MAX_SECONDS:
            time_score = max(0.1, 1.0 - (time_diff_sec / TIME_WINDOW_MAX_SECONDS) * 0.9)
        else:
            time_score = 0.0

        # Component scores
        order_score = 1.0 if same_order else 0.0
        amount_score = 1.0 if same_amt else max(0.0, 1.0 - (amt_diff / max(amt1, amt2, 1.0)))
        utr_score = 1.0 if same_utr else ref_sim

        # Composite score
        dup_score = round(
            WEIGHT_UTR * utr_score
            + WEIGHT_AMOUNT * amount_score
            + WEIGHT_ORDER * order_score
            + WEIGHT_TIME * time_score,
            4,
        )

        # Classification Rule:
        # 1. Exact Duplicate: Same UTR + same amount
        if same_utr and same_amt:
            classification = DuplicateClassification.DUPLICATE.value
            reason = f"Confirmed duplicate payment: identical UTR ({utr1}) and amount (INR {amt1:.2f})"
        # 2. Ambiguous Multi-Payment Candidate: Same order + same amount, but distinct UTRs (retry attempt)
        elif same_order and same_amt and not same_utr:
            classification = DuplicateClassification.AMBIGUOUS.value
            reason = f"Ambiguous candidate payment (retry): same order ({oid1}) and amount (INR {amt1:.2f}) with distinct UTRs ({utr1} vs {utr2})"
        # 3. Same UTR with amount discrepancy
        elif same_utr and not same_amt:
            classification = DuplicateClassification.AMBIGUOUS.value
            reason = f"Ambiguous collision: identical UTR ({utr1}) with mismatched amounts (INR {amt1:.2f} vs INR {amt2:.2f})"
        # 4. No duplicate
        else:
            classification = DuplicateClassification.NO_DUPLICATE.value
            reason = "Distinct independent transactions"

        return DuplicateEvidence(
            payment_id_1=pid1,
            payment_id_2=pid2,
            order_id_1=oid1,
            order_id_2=oid2,
            same_order=same_order,
            same_amount=same_amt,
            amount_1=amt1,
            amount_2=amt2,
            amount_difference=amt_diff,
            same_utr=same_utr,
            utr_1=utr1,
            utr_2=utr2,
            reference_similarity=ref_sim,
            timestamp_difference_seconds=time_diff_sec,
            same_payment_method=same_method,
            duplicate_score=dup_score,
            classification=classification,
            reason=reason,
        )

    def detect_duplicates_for_order(self, order_id: str) -> DuplicateDetectionResult:
        """Evaluate duplicate status for all payments associated with an order."""
        payments = self.payments_by_order.get(order_id, [])

        # 0 or 1 payment -> NO_DUPLICATE
        if len(payments) <= 1:
            pid = payments[0]["payment_id"] if payments else None
            return DuplicateDetectionResult(
                order_id=order_id,
                classification=DuplicateClassification.NO_DUPLICATE,
                primary_payment_id=pid,
                duplicate_payment_ids=[],
                candidate_pairs=[],
                confidence=1.0,
                reason="Single or zero payment records associated with order",
            )

        # Multiple payments on same order
        # Evaluate all pair combinations within this order
        candidate_pairs: list[DuplicateEvidence] = []
        has_confirmed_duplicate = False
        has_ambiguous_candidate = False

        for i in range(len(payments)):
            for j in range(i + 1, len(payments)):
                ev = self.evaluate_pair(payments[i], payments[j])
                candidate_pairs.append(ev)
                if ev.classification == DuplicateClassification.DUPLICATE.value:
                    has_confirmed_duplicate = True
                elif ev.classification == DuplicateClassification.AMBIGUOUS.value:
                    has_ambiguous_candidate = True

        # Determine overall classification
        primary_id = payments[0]["payment_id"]
        other_ids = [p["payment_id"] for p in payments[1:]]

        if has_confirmed_duplicate:
            return DuplicateDetectionResult(
                order_id=order_id,
                classification=DuplicateClassification.DUPLICATE,
                primary_payment_id=primary_id,
                duplicate_payment_ids=other_ids,
                candidate_pairs=candidate_pairs,
                confidence=0.95,
                reason=f"Confirmed duplicate payment transaction found on order {order_id}",
            )

        if has_ambiguous_candidate:
            return DuplicateDetectionResult(
                order_id=order_id,
                classification=DuplicateClassification.AMBIGUOUS,
                primary_payment_id=primary_id,
                duplicate_payment_ids=other_ids,
                candidate_pairs=candidate_pairs,
                confidence=0.70,
                reason=f"Multiple ({len(payments)}) candidate payments with distinct references found on order {order_id}; customer retry attempt",
            )

        return DuplicateDetectionResult(
            order_id=order_id,
            classification=DuplicateClassification.NO_DUPLICATE,
            primary_payment_id=primary_id,
            duplicate_payment_ids=[],
            candidate_pairs=candidate_pairs,
            confidence=1.0,
            reason="Multiple distinct payments without duplication",
        )

    def detect_all(self) -> list[DuplicateDetectionResult]:
        """Evaluate duplicate status across all orders in deterministic order."""
        # Include all known orders + any orphan orders from payments
        all_order_ids = sorted(
            set(self.orders.keys()) | set(self.payments_by_order.keys())
        )
        return [self.detect_duplicates_for_order(oid) for oid in all_order_ids]

    def detect_cross_order_duplicate_utrs(self) -> list[DuplicateEvidence]:
        """Detect any duplicate UTRs across different orders."""
        cross_order_duplicates: list[DuplicateEvidence] = []
        for utr, payments in self.payments_by_utr.items():
            if len(payments) > 1:
                # Check if they span different orders
                distinct_orders = {p.get("order_id") for p in payments if p.get("order_id")}
                if len(distinct_orders) > 1:
                    for i in range(len(payments)):
                        for j in range(i + 1, len(payments)):
                            if payments[i].get("order_id") != payments[j].get("order_id"):
                                ev = self.evaluate_pair(payments[i], payments[j])
                                cross_order_duplicates.append(ev)
        return cross_order_duplicates

    def get_summary(self, results: list[DuplicateDetectionResult] | None = None) -> dict[str, Any]:
        """Generate summary statistics of duplicate detection."""
        if results is None:
            results = self.detect_all()

        total = len(results)
        dup_count = sum(1 for r in results if r.classification == DuplicateClassification.DUPLICATE)
        ambig_count = sum(1 for r in results if r.classification == DuplicateClassification.AMBIGUOUS)
        no_dup_count = sum(1 for r in results if r.classification == DuplicateClassification.NO_DUPLICATE)

        # Count total candidate pairs examined
        total_pairs_examined = sum(len(r.candidate_pairs) for r in results)

        return {
            "total_orders_evaluated": total,
            "total_payments_indexed": len(self.payments),
            "candidate_pairs_examined": total_pairs_examined,
            "duplicates_detected": dup_count,
            "duplicates_percentage": round((dup_count / total) * 100, 2) if total else 0.0,
            "ambiguous_candidate_groups": ambig_count,
            "ambiguous_percentage": round((ambig_count / total) * 100, 2) if total else 0.0,
            "no_duplicate_cases": no_dup_count,
            "no_duplicate_percentage": round((no_dup_count / total) * 100, 2) if total else 0.0,
        }

