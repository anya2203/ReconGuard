"""Deterministic Fuzzy Matching Engine for ReconGuard.

Performs multi-dimensional candidate discovery and transparent, explainable scoring
for ambiguous or slightly discrepant financial records:
- Rounding / micro-amount variances (< ₹1.00)
- Reference / UTR character typos (transpositions, OCR errors)
- Date-window timing tolerances
- Candidate disambiguation

Operates exclusively on operational data with ZERO ground-truth leakage.
"""

import csv
import difflib
from datetime import datetime
from pathlib import Path
from typing import Any

from app.matching.exact_matcher import ExactMatcher
from app.matching.types import (
    ConfidenceBand,
    ExactMatchEvidence,
    FuzzyMatchEvidence,
    MatchMethod,
    MatchResult,
    MatchStatus,
)

# Default matching thresholds & tolerances
DEFAULT_AMOUNT_TOLERANCE_ABS = 1.00  # ₹1.00 absolute micro-rounding tolerance
DEFAULT_AMOUNT_TOLERANCE_PCT = 0.01  # 1.0% percentage tolerance
DEFAULT_DATE_WINDOW_DAYS = 14.0  # 14-day candidate search window
MAX_POLICY_SLA_DAYS = 5.0  # Standard settlement SLA window

# Transparent scoring weights (sum to 1.00)
WEIGHT_AMOUNT = 0.35
WEIGHT_REFERENCE = 0.30
WEIGHT_RELATIONSHIP = 0.20
WEIGHT_DATE = 0.15

# Confidence band thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.88
MEDIUM_CONFIDENCE_THRESHOLD = 0.65


class FuzzyMatcher:
    """Multi-dimensional fuzzy matcher with explainable scoring."""

    def __init__(
        self,
        orders: list[dict[str, Any]],
        payments: list[dict[str, Any]],
        settlements: list[dict[str, Any]],
        invoices: list[dict[str, Any]],
        adjustments: list[dict[str, Any]] | None = None,
        amount_tolerance_abs: float = DEFAULT_AMOUNT_TOLERANCE_ABS,
        amount_tolerance_pct: float = DEFAULT_AMOUNT_TOLERANCE_PCT,
        date_window_days: float = DEFAULT_DATE_WINDOW_DAYS,
    ):
        self.orders = {o["order_id"]: o for o in orders}
        self.amount_tolerance_abs = amount_tolerance_abs
        self.amount_tolerance_pct = amount_tolerance_pct
        self.date_window_days = date_window_days

        # Internal exact matcher for fast-path 1:1 evaluation
        self.exact_matcher = ExactMatcher(
            orders=orders,
            payments=payments,
            settlements=settlements,
            invoices=invoices,
            adjustments=adjustments,
        )

        # Index payments
        self.payments = payments
        self.payments_by_order: dict[str, list[dict[str, Any]]] = {}
        self.payments_by_id: dict[str, dict[str, Any]] = {}
        self.payments_by_utr: dict[str, dict[str, Any]] = {}
        for p in payments:
            oid = p["order_id"]
            self.payments_by_order.setdefault(oid, []).append(p)
            self.payments_by_id[p["payment_id"]] = p
            utr = p.get("utr", "").strip()
            if utr:
                self.payments_by_utr[utr] = p

        # Index settlements
        self.settlements = settlements
        self.settlements_by_utr: dict[str, list[dict[str, Any]]] = {}
        self.settlements_by_id: dict[str, dict[str, Any]] = {}
        for s in settlements:
            utr = s.get("utr", "").strip()
            if utr:
                self.settlements_by_utr.setdefault(utr, []).append(s)
            self.settlements_by_id[s["settlement_id"]] = s

        # Index invoices
        self.invoices_by_order: dict[str, list[dict[str, Any]]] = {}
        for inv in invoices:
            oid = inv["order_id"]
            self.invoices_by_order.setdefault(oid, []).append(inv)

        # Index adjustments
        self.adjustments_by_related_id: dict[str, list[dict[str, Any]]] = {}
        if adjustments:
            for adj in adjustments:
                rid = adj.get("related_id", "").strip()
                if rid:
                    self.adjustments_by_related_id.setdefault(rid, []).append(adj)

    @classmethod
    def from_csv_directory(
        cls,
        data_dir: Path | str,
        amount_tolerance_abs: float = DEFAULT_AMOUNT_TOLERANCE_ABS,
        amount_tolerance_pct: float = DEFAULT_AMOUNT_TOLERANCE_PCT,
        date_window_days: float = DEFAULT_DATE_WINDOW_DAYS,
    ) -> "FuzzyMatcher":
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
        settlements = load_csv("settlements.csv")
        invoices = load_csv("invoices.csv")
        adjustments = load_csv("adjustments.csv")

        return cls(
            orders=orders,
            payments=payments,
            settlements=settlements,
            invoices=invoices,
            adjustments=adjustments,
            amount_tolerance_abs=amount_tolerance_abs,
            amount_tolerance_pct=amount_tolerance_pct,
            date_window_days=date_window_days,
        )

    # ------------------------------------------------------------------------
    # SCORING HELPERS
    # ------------------------------------------------------------------------

    def calc_amount_similarity(self, amount1: float, amount2: float) -> tuple[float, float, float]:
        """Compute amount similarity score (0.0 to 1.0), absolute diff, and pct diff."""
        abs_diff = round(abs(amount1 - amount2), 2)
        base = max(amount1, amount2, 1.0)
        pct_diff = round(abs_diff / base, 4)

        if abs_diff <= 0.001:
            return 1.0, abs_diff, pct_diff

        # Micro-rounding variance (e.g. ₹0.05 GST rounding difference)
        if abs_diff <= self.amount_tolerance_abs:
            score = 1.0 - (abs_diff / self.amount_tolerance_abs) * 0.05
            return round(score, 4), abs_diff, pct_diff

        # Percentage tolerance window
        if pct_diff <= self.amount_tolerance_pct:
            score = 0.95 - (pct_diff / self.amount_tolerance_pct) * 0.20
            return round(score, 4), abs_diff, pct_diff

        # Large amount discrepancy (e.g. 30% difference)
        score = max(0.0, 1.0 - (pct_diff * 2.0))
        return round(score, 4), abs_diff, pct_diff

    def calc_reference_similarity(self, ref1: str | None, ref2: str | None) -> float:
        """Compute string similarity ratio between two references (0.0 to 1.0)."""
        r1 = (ref1 or "").strip()
        r2 = (ref2 or "").strip()

        if not r1 or not r2:
            return 0.0

        if r1 == r2:
            return 1.0

        return round(difflib.SequenceMatcher(None, r1, r2).ratio(), 4)

    def calc_date_similarity(
        self, date_str1: str | None, date_str2: str | None
    ) -> tuple[float, float]:
        """Compute date proximity score (0.0 to 1.0) and difference in days."""
        if not date_str1 or not date_str2:
            return 0.0, 999.0

        try:
            dt1 = datetime.fromisoformat(date_str1)
            dt2 = datetime.fromisoformat(date_str2)
            diff_days = round(abs((dt2 - dt1).total_seconds()) / 86400.0, 2)

            # Within normal SLA (T+1 / T+2 days)
            if diff_days <= 2.0:
                return 1.0, diff_days

            # Within fuzzy search window (e.g. up to 14 days)
            if diff_days <= self.date_window_days:
                score = 1.0 - (diff_days / self.date_window_days) * 0.35
                return round(score, 4), diff_days

            return 0.0, diff_days
        except Exception:
            return 0.0, 999.0

    # ------------------------------------------------------------------------
    # CANDIDATE DISCOVERY & EVALUATION
    # ------------------------------------------------------------------------

    def find_settlement_candidates(
        self, payment: dict[str, Any], order: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Discover and rank candidate settlement records for a given payment/order."""
        pay_utr = payment.get("utr", "").strip()
        pay_amount = float(payment.get("amount", 0.0))
        pay_created = payment.get("created_at")

        candidates: list[dict[str, Any]] = []

        # 1. Check exact UTR matches first
        if pay_utr and pay_utr in self.settlements_by_utr:
            for s in self.settlements_by_utr[pay_utr]:
                candidates.append({"settlement": s, "discovery_method": "EXACT_UTR"})
            return candidates

        # 2. Check near-UTR candidate settlements (e.g. transposed digits in REFERENCE_TYPO)
        # Narrow down by prefix or candidate length before calling SequenceMatcher
        prefix = pay_utr[:8] if len(pay_utr) >= 8 else pay_utr
        for s in self.settlements:
            s_utr = s.get("utr", "").strip()
            if not s_utr:
                continue

            # Exclude settlements that already have an exact 1:1 matching payment
            if s_utr in self.payments_by_utr:
                continue

            # Fast prefix filter
            if prefix and not s_utr.startswith(prefix):
                continue

            ref_sim = self.calc_reference_similarity(pay_utr, s_utr)
            if ref_sim >= 0.85:
                candidates.append({"settlement": s, "discovery_method": "FUZZY_SCAN"})

        return candidates

    def match_order(self, order_id: str) -> MatchResult:
        """Evaluate matching for a single order using exact fast-path and fuzzy scoring."""
        # 1. Exact Match Fast-Path (O(1))
        exact_res = self.exact_matcher.match_order(order_id)
        if exact_res.status == MatchStatus.MATCHED:
            exact_res.confidence_band = ConfidenceBand.HIGH.value
            return exact_res

        # 2. Evaluate Unresolved Cases with Fuzzy Matching
        order = self.orders.get(order_id)
        if not order:
            return exact_res

        order_amount = float(order.get("amount", 0.0))
        order_status = order.get("status", "")

        # Incomplete / Abandoned Order Guard
        if order_status != "COMPLETED":
            return exact_res

        # Payment Retrieval
        payments = self.payments_by_order.get(order_id, [])
        if len(payments) == 0:
            return exact_res

        # Multiple Payments (Ambiguous Duplicate Check)
        if len(payments) > 1:
            return exact_res

        payment = payments[0]
        pay_id = payment["payment_id"]
        pay_amount = float(payment.get("amount", 0.0))
        pay_status = payment.get("status", "")
        pay_utr = payment.get("utr", "").strip()

        # Active Adjustments Guard (Chargebacks / Refunds)
        related_adjs = (
            self.adjustments_by_related_id.get(pay_id, [])
            + self.adjustments_by_related_id.get(order_id, [])
        )
        if len(related_adjs) > 0:
            return exact_res

        # Non-SUCCESS payment
        if pay_status != "SUCCESS":
            return exact_res

        # Order-Payment Amount Similarity
        order_pay_sim, order_pay_abs_diff, order_pay_pct_diff = self.calc_amount_similarity(
            order_amount, pay_amount
        )

        # Hard guardrail: Large amount discrepancy (> 5% difference) cannot be matched
        if order_pay_pct_diff > 0.05 and order_pay_abs_diff > self.amount_tolerance_abs:
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.DISCREPANCY,
                match_method=MatchMethod.NONE,
                payment_ids=[pay_id],
                confidence=0.3,
                confidence_band=ConfidenceBand.LOW.value,
                financial_impact=order_pay_abs_diff,
                reason=f"Large amount mismatch: order INR {order_amount:.2f} vs payment INR {pay_amount:.2f} (diff: INR {order_pay_abs_diff:.2f})",
            )

        # Settlement Candidate Discovery & Scoring
        settlement_candidates = self.find_settlement_candidates(payment, order)
        if not settlement_candidates:
            return exact_res

        # Evaluate candidate settlements
        scored_candidates: list[dict[str, Any]] = []
        for cand in settlement_candidates:
            settle = cand["settlement"]
            s_id = settle["settlement_id"]
            s_utr = settle.get("utr", "").strip()
            s_amount = float(settle.get("amount", 0.0))
            s_fees = float(settle.get("fees", 0.0))
            expected_net = round(pay_amount - s_fees, 2)

            # Amount score: net settlement amount vs single order expected net
            pay_settle_sim, pay_settle_diff, _ = self.calc_amount_similarity(
                s_amount, expected_net
            )

            # Check if this settlement is a multi-order batch
            is_batch_settlement = "BATCH" in s_id or (s_amount > expected_net * 1.5)
            if is_batch_settlement:
                pay_settle_sim = 0.40

            # Reference similarity
            ref_sim = self.calc_reference_similarity(pay_utr, s_utr)

            # Date similarity
            date_sim, date_diff_days = self.calc_date_similarity(
                payment.get("created_at"), settle.get("settled_at")
            )

            # Relationship score
            rel_score = 1.0

            # Invoice factor
            invoices = self.invoices_by_order.get(order_id, [])
            inv_id = invoices[0]["invoice_id"] if invoices else None

            # Composite amount score
            composite_amt_score = round((order_pay_sim + pay_settle_sim) / 2.0, 4)

            # Composite final score
            final_score = round(
                WEIGHT_AMOUNT * composite_amt_score
                + WEIGHT_REFERENCE * ref_sim
                + WEIGHT_RELATIONSHIP * rel_score
                + WEIGHT_DATE * date_sim,
                4,
            )

            # Confidence categorization
            if final_score >= HIGH_CONFIDENCE_THRESHOLD:
                conf_band = ConfidenceBand.HIGH.value
            elif final_score >= MEDIUM_CONFIDENCE_THRESHOLD:
                conf_band = ConfidenceBand.MEDIUM.value
            else:
                conf_band = ConfidenceBand.LOW.value

            scored_candidates.append(
                {
                    "settlement_id": s_id,
                    "settlement_utr": s_utr,
                    "settlement_amount": s_amount,
                    "settlement_fees": s_fees,
                    "expected_net": expected_net,
                    "is_batch": is_batch_settlement,
                    "amount_score": composite_amt_score,
                    "reference_score": ref_sim,
                    "date_score": date_sim,
                    "relationship_score": rel_score,
                    "final_score": final_score,
                    "confidence_band": conf_band,
                    "date_diff_days": date_diff_days,
                    "order_pay_diff": order_pay_abs_diff,
                    "pay_settle_diff": pay_settle_diff,
                    "invoice_id": inv_id,
                }
            )

        # Sort candidates descending by score
        scored_candidates.sort(key=lambda x: x["final_score"], reverse=True)
        top = scored_candidates[0]

        # Multi-candidate ambiguity check:
        # If top 2 candidates have identical or near-identical scores (score diff < 0.01)
        if len(scored_candidates) > 1:
            second = scored_candidates[1]
            if (
                top["final_score"] >= MEDIUM_CONFIDENCE_THRESHOLD
                and abs(top["final_score"] - second["final_score"]) < 0.01
            ):
                return MatchResult(
                    order_id=order_id,
                    status=MatchStatus.AMBIGUOUS,
                    match_method=MatchMethod.NONE,
                    payment_ids=[pay_id],
                    settlement_ids=[top["settlement_id"], second["settlement_id"]],
                    confidence=top["final_score"],
                    confidence_band=ConfidenceBand.MEDIUM.value,
                    evidence=FuzzyMatchEvidence(
                        candidate_payment_id=pay_id,
                        candidate_settlement_id=top["settlement_id"],
                        final_score=top["final_score"],
                        confidence_band=ConfidenceBand.MEDIUM.value,
                        top_candidates=scored_candidates[:3],
                    ),
                    reason=f"Ambiguous candidates: multiple settlements with near-identical scores ({top['final_score']:.2f} vs {second['final_score']:.2f})",
                )

        # Guard against multi-order batch settlement false 1:1 match
        if top["is_batch"]:
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.AMBIGUOUS,
                match_method=MatchMethod.NONE,
                payment_ids=[pay_id],
                settlement_ids=[top["settlement_id"]],
                confidence=top["final_score"],
                confidence_band=ConfidenceBand.MEDIUM.value,
                financial_impact=top["pay_settle_diff"],
                reason=f"Settlement '{top['settlement_id']}' is a multi-order batch payout; requires aggregation matching",
            )

        # Build Explainable Fuzzy Evidence
        evidence = FuzzyMatchEvidence(
            candidate_payment_id=pay_id,
            candidate_settlement_id=top["settlement_id"],
            amount_difference=top["order_pay_diff"],
            amount_difference_percentage=order_pay_pct_diff,
            date_difference_days=top["date_diff_days"],
            reference_similarity=top["reference_score"],
            amount_score=top["amount_score"],
            reference_score=top["reference_score"],
            date_score=top["date_score"],
            relationship_score=top["relationship_score"],
            final_score=top["final_score"],
            confidence_band=top["confidence_band"],
            top_candidates=scored_candidates[:3],
        )

        # High Confidence Fuzzy Match (e.g. Rounding Mismatch, Reference Typo)
        if top["final_score"] >= HIGH_CONFIDENCE_THRESHOLD:
            # Check SLA
            if top["date_diff_days"] > MAX_POLICY_SLA_DAYS:
                evidence.failed_checks.append("settlement_sla_policy")
                return MatchResult(
                    order_id=order_id,
                    status=MatchStatus.DISCREPANCY,
                    match_method=MatchMethod.FUZZY,
                    payment_ids=[pay_id],
                    settlement_ids=[top["settlement_id"]],
                    invoice_id=top["invoice_id"],
                    confidence=top["final_score"],
                    confidence_band=ConfidenceBand.HIGH.value,
                    evidence=evidence,
                    reason=f"High-confidence fuzzy match found ({top['final_score']:.2f}), but settlement delay ({top['date_diff_days']:.1f} days) exceeds 5-day SLA policy",
                )

            # Check invoice existence
            if top["invoice_id"] is None:
                evidence.failed_checks.append("invoice_exists")
                return MatchResult(
                    order_id=order_id,
                    status=MatchStatus.DISCREPANCY,
                    match_method=MatchMethod.FUZZY,
                    payment_ids=[pay_id],
                    settlement_ids=[top["settlement_id"]],
                    invoice_id=None,
                    confidence=top["final_score"],
                    confidence_band=ConfidenceBand.HIGH.value,
                    evidence=evidence,
                    reason=f"High-confidence fuzzy match found ({top['final_score']:.2f}), but invoice record is missing for order",
                )

            # Valid High-Confidence Fuzzy Match (Rounding or Typo)
            evidence.matched_checks.append("high_confidence_fuzzy_score")
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.MATCHED,
                match_method=MatchMethod.FUZZY,
                payment_ids=[pay_id],
                settlement_ids=[top["settlement_id"]],
                invoice_id=top["invoice_id"],
                confidence=top["final_score"],
                confidence_band=ConfidenceBand.HIGH.value,
                financial_impact=top["order_pay_diff"],
                evidence=evidence,
                reason=f"Fuzzy match verified with HIGH confidence ({top['final_score']:.2f}); reference similarity {top['reference_score']:.2f}, amount diff INR {top['order_pay_diff']:.2f}",
            )

        # Medium Confidence
        if top["final_score"] >= MEDIUM_CONFIDENCE_THRESHOLD:
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.DISCREPANCY,
                match_method=MatchMethod.FUZZY,
                payment_ids=[pay_id],
                settlement_ids=[top["settlement_id"]],
                invoice_id=top["invoice_id"],
                confidence=top["final_score"],
                confidence_band=ConfidenceBand.MEDIUM.value,
                financial_impact=top["order_pay_diff"],
                evidence=evidence,
                reason=f"Plausible candidate found with MEDIUM confidence ({top['final_score']:.2f}); exceeds exact tolerance thresholds",
            )

        # Low Confidence
        return MatchResult(
            order_id=order_id,
            status=MatchStatus.UNMATCHED,
            match_method=MatchMethod.NONE,
            payment_ids=[pay_id],
            confidence=top["final_score"],
            confidence_band=ConfidenceBand.LOW.value,
            financial_impact=order_amount,
            evidence=evidence,
            reason=f"Candidate score ({top['final_score']:.2f}) below acceptable threshold",
        )

    def match_all(self) -> list[MatchResult]:
        """Execute matching across all orders in deterministic order."""
        sorted_order_ids = sorted(self.orders.keys())
        return [self.match_order(oid) for oid in sorted_order_ids]

    def get_summary(self, results: list[MatchResult] | None = None) -> dict[str, Any]:
        """Generate breakdown statistics from matching results."""
        if results is None:
            results = self.match_all()

        total = len(results)
        matched_exact = sum(
            1 for r in results if r.status == MatchStatus.MATCHED and r.match_method == MatchMethod.EXACT
        )
        matched_fuzzy = sum(
            1 for r in results if r.status == MatchStatus.MATCHED and r.match_method == MatchMethod.FUZZY
        )
        matched_total = matched_exact + matched_fuzzy
        ambiguous = sum(1 for r in results if r.status == MatchStatus.AMBIGUOUS)
        unmatched = sum(1 for r in results if r.status == MatchStatus.UNMATCHED)
        discrepancy = sum(1 for r in results if r.status == MatchStatus.DISCREPANCY)

        conf_high = sum(1 for r in results if r.confidence_band == ConfidenceBand.HIGH.value)
        conf_med = sum(1 for r in results if r.confidence_band == ConfidenceBand.MEDIUM.value)
        conf_low = sum(1 for r in results if r.confidence_band == ConfidenceBand.LOW.value)
        conf_none = sum(1 for r in results if r.confidence_band == ConfidenceBand.NONE.value)

        return {
            "total_processed": total,
            "matched_total": matched_total,
            "matched_total_percentage": round((matched_total / total) * 100, 2) if total else 0.0,
            "matched_exact": matched_exact,
            "matched_exact_percentage": round((matched_exact / total) * 100, 2) if total else 0.0,
            "matched_fuzzy": matched_fuzzy,
            "matched_fuzzy_percentage": round((matched_fuzzy / total) * 100, 2) if total else 0.0,
            "ambiguous": ambiguous,
            "ambiguous_percentage": round((ambiguous / total) * 100, 2) if total else 0.0,
            "unmatched": unmatched,
            "unmatched_percentage": round((unmatched / total) * 100, 2) if total else 0.0,
            "discrepancy": discrepancy,
            "discrepancy_percentage": round((discrepancy / total) * 100, 2) if total else 0.0,
            "confidence_distribution": {
                "HIGH": conf_high,
                "MEDIUM": conf_med,
                "LOW": conf_low,
                "NONE": conf_none,
            },
        }
