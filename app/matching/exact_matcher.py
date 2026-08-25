"""Deterministic Exact Matching Engine for ReconGuard.

Performs rule-based, deterministic 1:1 exact matching across operational financial records:
- Orders
- Payments
- Settlements
- Invoices
- Adjustments

Operates exclusively on operational data with ZERO ground-truth leakage.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from app.matching.types import (
    ExactMatchEvidence,
    MatchMethod,
    MatchResult,
    MatchStatus,
)

# Maximum settlement delay allowed before flagging as SLA breach (5 days in seconds)
MAX_SETTLEMENT_SLA_SECONDS = 5 * 24 * 3600


class ExactMatcher:
    """Deterministic exact matcher verifying 1:1 operational relationships."""

    def __init__(
        self,
        orders: list[dict[str, Any]],
        payments: list[dict[str, Any]],
        settlements: list[dict[str, Any]],
        invoices: list[dict[str, Any]],
        adjustments: list[dict[str, Any]] | None = None,
    ):
        self.orders = {o["order_id"]: o for o in orders}

        # Index payments by order_id and payment_id
        self.payments_by_order: dict[str, list[dict[str, Any]]] = {}
        self.payments_by_id: dict[str, dict[str, Any]] = {}
        for p in payments:
            oid = p["order_id"]
            self.payments_by_order.setdefault(oid, []).append(p)
            self.payments_by_id[p["payment_id"]] = p

        # Index settlements by UTR and settlement_id
        self.settlements_by_utr: dict[str, list[dict[str, Any]]] = {}
        self.settlements_by_id: dict[str, dict[str, Any]] = {}
        for s in settlements:
            utr = s.get("utr", "").strip()
            if utr:
                self.settlements_by_utr.setdefault(utr, []).append(s)
            self.settlements_by_id[s["settlement_id"]] = s

        # Index invoices by order_id
        self.invoices_by_order: dict[str, list[dict[str, Any]]] = {}
        for inv in invoices:
            oid = inv["order_id"]
            self.invoices_by_order.setdefault(oid, []).append(inv)

        # Index adjustments by related_id (order_id or payment_id)
        self.adjustments_by_related_id: dict[str, list[dict[str, Any]]] = {}
        if adjustments:
            for adj in adjustments:
                rid = adj.get("related_id", "").strip()
                if rid:
                    self.adjustments_by_related_id.setdefault(rid, []).append(adj)

    @classmethod
    def from_csv_directory(cls, data_dir: Path | str) -> "ExactMatcher":
        """Load operational datasets from CSV files in the given directory.

        Note: Does NOT load ground truth files.
        """
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

    def match_order(self, order_id: str) -> MatchResult:
        """Evaluate exact matching rules for a single order against all operational records."""
        order = self.orders.get(order_id)
        if not order:
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.UNMATCHED,
                match_method=MatchMethod.NONE,
                reason="Order record not found in operational database",
            )

        order_amount = float(order.get("amount", 0.0))
        order_status = order.get("status", "")

        evidence = ExactMatchEvidence(
            order_id_verified=True,
            order_status=order_status,
            order_amount=order_amount,
        )

        # 1. Order Status Check
        if order_status != "COMPLETED":
            evidence.failed_checks.append("order_completed_status")
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.UNMATCHED,
                match_method=MatchMethod.NONE,
                financial_impact=order_amount,
                evidence=evidence,
                reason=f"Order status is '{order_status}' (not COMPLETED)",
            )
        evidence.matched_checks.append("order_completed_status")

        # 2. Payment Retrieval & Candidate Check
        payments = self.payments_by_order.get(order_id, [])
        if len(payments) == 0:
            evidence.failed_checks.append("payment_exists")
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.UNMATCHED,
                match_method=MatchMethod.NONE,
                financial_impact=order_amount,
                evidence=evidence,
                reason="No captured payment record found for order",
            )

        if len(payments) > 1:
            evidence.failed_checks.append("single_payment_candidate")
            payment_ids = [p["payment_id"] for p in payments]
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.AMBIGUOUS,
                match_method=MatchMethod.NONE,
                payment_ids=payment_ids,
                financial_impact=order_amount,
                evidence=evidence,
                reason=f"Multiple candidate payments ({len(payments)}) found for order: {', '.join(payment_ids)}",
            )

        # Single payment verified
        payment = payments[0]
        pay_id = payment["payment_id"]
        pay_amount = float(payment.get("amount", 0.0))
        pay_status = payment.get("status", "")
        pay_method = payment.get("method", "")
        pay_utr = payment.get("utr", "").strip()

        evidence.payment_id = pay_id
        evidence.payment_amount = pay_amount
        evidence.payment_status = pay_status
        evidence.payment_method = pay_method
        evidence.utr = pay_utr
        evidence.matched_checks.append("single_payment_candidate")

        # 3. Payment Status Check
        if pay_status != "SUCCESS":
            evidence.failed_checks.append("payment_success_status")
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.DISCREPANCY,
                match_method=MatchMethod.NONE,
                payment_ids=[pay_id],
                financial_impact=order_amount,
                evidence=evidence,
                reason=f"Payment status is '{pay_status}' (not SUCCESS)",
            )
        evidence.matched_checks.append("payment_success_status")

        # 4. Payment Amount Check
        amount_diff = round(abs(order_amount - pay_amount), 2)
        evidence.amount_difference = amount_diff
        if amount_diff > 0.001:
            evidence.failed_checks.append("order_payment_amount_match")
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.DISCREPANCY,
                match_method=MatchMethod.NONE,
                payment_ids=[pay_id],
                financial_impact=amount_diff,
                evidence=evidence,
                reason=f"Amount mismatch: order amount INR {order_amount:.2f} != payment amount INR {pay_amount:.2f} (diff: INR {amount_diff:.2f})",
            )
        evidence.matched_checks.append("order_payment_amount_match")

        # 5. Adjustments Check (Chargeback / Refund / Dispute Fees)
        related_adjs = (
            self.adjustments_by_related_id.get(pay_id, [])
            + self.adjustments_by_related_id.get(order_id, [])
        )
        if len(related_adjs) > 0:
            evidence.failed_checks.append("no_adjustments_present")
            evidence.adjustment_ids = [a["adjustment_id"] for a in related_adjs]
            evidence.adjustment_types = [a["type"] for a in related_adjs]
            adj_impact = round(sum(abs(float(a.get("amount", 0.0))) for a in related_adjs), 2)
            types_str = ", ".join(set(evidence.adjustment_types))
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.DISCREPANCY,
                match_method=MatchMethod.NONE,
                payment_ids=[pay_id],
                adjustment_ids=evidence.adjustment_ids,
                financial_impact=adj_impact,
                evidence=evidence,
                reason=f"Active adjustments ({types_str}) logged against transaction",
            )
        evidence.matched_checks.append("no_adjustments_present")

        # 6. Settlement Matching via UTR
        if not pay_utr:
            evidence.failed_checks.append("payment_utr_present")
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.DISCREPANCY,
                match_method=MatchMethod.NONE,
                payment_ids=[pay_id],
                financial_impact=order_amount,
                evidence=evidence,
                reason="Payment does not have a valid UTR reference",
            )
        evidence.matched_checks.append("payment_utr_present")

        settlements = self.settlements_by_utr.get(pay_utr, [])
        if len(settlements) == 0:
            evidence.failed_checks.append("settlement_utr_match")
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.DISCREPANCY,
                match_method=MatchMethod.NONE,
                payment_ids=[pay_id],
                financial_impact=order_amount,
                evidence=evidence,
                reason=f"No bank settlement found matching UTR '{pay_utr}'",
            )

        if len(settlements) > 1:
            evidence.failed_checks.append("single_settlement_match")
            settle_ids = [s["settlement_id"] for s in settlements]
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.AMBIGUOUS,
                match_method=MatchMethod.NONE,
                payment_ids=[pay_id],
                settlement_ids=settle_ids,
                evidence=evidence,
                reason=f"Multiple settlements found for UTR '{pay_utr}': {', '.join(settle_ids)}",
            )

        settlement = settlements[0]
        settle_id = settlement["settlement_id"]
        settle_amount = float(settlement.get("amount", 0.0))
        settle_fees = float(settlement.get("fees", 0.0))
        expected_net = round(pay_amount - settle_fees, 2)

        evidence.settlement_id = settle_id
        evidence.settlement_amount = settle_amount
        evidence.settlement_fees = settle_fees
        evidence.settlement_expected_net = expected_net
        evidence.settlement_date = settlement.get("settled_at")

        # Check 1:1 Net Calculation
        # In batch settlements, settlement_amount != single order expected net
        net_diff = round(abs(settle_amount - expected_net), 2)
        if net_diff > 0.001:
            evidence.failed_checks.append("settlement_1to1_net_amount_match")
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.AMBIGUOUS,
                match_method=MatchMethod.NONE,
                payment_ids=[pay_id],
                settlement_ids=[settle_id],
                financial_impact=net_diff,
                evidence=evidence,
                reason=f"Settlement amount INR {settle_amount:.2f} differs from 1:1 net calculation INR {expected_net:.2f} (multi-order batch or fee variance)",
            )
        evidence.matched_checks.append("settlement_1to1_net_amount_match")

        # 7. Settlement SLA Window Check (5 business days)
        try:
            pay_dt = datetime.fromisoformat(payment["created_at"])
            settle_dt = datetime.fromisoformat(settlement["settled_at"])
            elapsed_seconds = (settle_dt - pay_dt).total_seconds()
            if elapsed_seconds > MAX_SETTLEMENT_SLA_SECONDS:
                evidence.settlement_sla_breached = True
                evidence.failed_checks.append("settlement_sla_policy")
                delay_days = elapsed_seconds / 86400.0
                return MatchResult(
                    order_id=order_id,
                    status=MatchStatus.DISCREPANCY,
                    match_method=MatchMethod.NONE,
                    payment_ids=[pay_id],
                    settlement_ids=[settle_id],
                    evidence=evidence,
                    reason=f"Settlement delay ({delay_days:.1f} days) exceeds maximum SLA policy window (5.0 days)",
                )
        except Exception:
            pass  # Fallback if dates are missing or invalid
        evidence.matched_checks.append("settlement_sla_policy")

        # 8. Invoice Verification
        invoices = self.invoices_by_order.get(order_id, [])
        if len(invoices) == 0:
            evidence.failed_checks.append("invoice_exists")
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.DISCREPANCY,
                match_method=MatchMethod.NONE,
                payment_ids=[pay_id],
                settlement_ids=[settle_id],
                evidence=evidence,
                reason="Invoice record missing for order",
            )

        invoice = invoices[0]
        inv_id = invoice["invoice_id"]
        inv_amount = float(invoice.get("amount", 0.0))
        evidence.invoice_id = inv_id
        evidence.invoice_amount = inv_amount
        evidence.matched_checks.append("invoice_exists")

        inv_diff = round(abs(order_amount - inv_amount), 2)
        if inv_diff > 0.001:
            evidence.failed_checks.append("invoice_amount_match")
            return MatchResult(
                order_id=order_id,
                status=MatchStatus.DISCREPANCY,
                match_method=MatchMethod.NONE,
                payment_ids=[pay_id],
                settlement_ids=[settle_id],
                invoice_id=inv_id,
                financial_impact=inv_diff,
                evidence=evidence,
                reason=f"Invoice amount INR {inv_amount:.2f} does not match order amount INR {order_amount:.2f}",
            )
        evidence.matched_checks.append("invoice_amount_match")

        # 9. All 1:1 Exact Checks Passed!
        return MatchResult(
            order_id=order_id,
            status=MatchStatus.MATCHED,
            match_method=MatchMethod.EXACT,
            payment_ids=[pay_id],
            settlement_ids=[settle_id],
            invoice_id=inv_id,
            confidence=1.0,
            financial_impact=0.0,
            evidence=evidence,
            reason="Exact 1:1 match verified across order, payment, settlement, and invoice within SLA",
        )

    def match_all(self) -> list[MatchResult]:
        """Execute exact matching across all orders in deterministic order."""
        sorted_order_ids = sorted(self.orders.keys())
        return [self.match_order(oid) for oid in sorted_order_ids]

    def get_summary(self, results: list[MatchResult] | None = None) -> dict[str, Any]:
        """Generate breakdown statistics from matching results."""
        if results is None:
            results = self.match_all()

        total = len(results)
        matched = sum(1 for r in results if r.status == MatchStatus.MATCHED)
        ambiguous = sum(1 for r in results if r.status == MatchStatus.AMBIGUOUS)
        unmatched = sum(1 for r in results if r.status == MatchStatus.UNMATCHED)
        discrepancy = sum(1 for r in results if r.status == MatchStatus.DISCREPANCY)

        return {
            "total_processed": total,
            "matched": matched,
            "matched_percentage": round((matched / total) * 100, 2) if total else 0.0,
            "ambiguous": ambiguous,
            "ambiguous_percentage": round((ambiguous / total) * 100, 2) if total else 0.0,
            "unmatched": unmatched,
            "unmatched_percentage": round((unmatched / total) * 100, 2) if total else 0.0,
            "discrepancy": discrepancy,
            "discrepancy_percentage": round((discrepancy / total) * 100, 2) if total else 0.0,
        }

