"""Synthetic Financial Reconciliation Dataset Generator for ReconGuard.

Generates realistic, deterministic financial reconciliation datasets and ground-truth
evaluation datasets for the Razorpay Buildathon 2026.

Key Target Distribution (1,000 cases):
- ~78% Deterministic Resolution (780 cases)
- ~12% Deterministic Escalation (120 cases)
- ~10% AI Investigation (100 cases: 50 AI-Resolvable, 50 AI-Escalation)
"""

import argparse
import json
import math
import os
import random
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# ============================================================================
# CONSTANTS & CONFIGURATION
# ============================================================================

DEFAULT_SEED = 42
DEFAULT_TOTAL_CASES = 1000
DATASET_VERSION = "v1.0.0"
DEFAULT_ANCHOR_DATETIME = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)

# Realistic INR transaction amounts
REALISTIC_AMOUNTS = [
    299.00,
    499.00,
    799.00,
    999.00,
    1299.00,
    1499.50,
    1999.00,
    2499.00,
    2999.00,
    3499.00,
    4999.00,
    7500.00,
    9999.00,
    14999.00,
    25000.00,
    49999.00,
]

PAYMENT_METHODS = ["UPI", "CARD", "NETBANKING", "WALLET"]


# ============================================================================
# CONTROLLED VOCABULARIES & ENUMS
# ============================================================================


class ScenarioType(str, Enum):
    """Controlled taxonomy of reconciliation scenarios."""

    EXACT_MATCH = "EXACT_MATCH"
    MULTI_ORDER_SETTLEMENT = "MULTI_ORDER_SETTLEMENT"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    DELAYED_SETTLEMENT = "DELAYED_SETTLEMENT"
    MISSING_PAYMENT = "MISSING_PAYMENT"
    CHARGEBACK_ADJUSTMENT = "CHARGEBACK_ADJUSTMENT"
    ROUNDING_MISMATCH = "ROUNDING_MISMATCH"
    REFERENCE_TYPO = "REFERENCE_TYPO"
    MISSING_INVOICE = "MISSING_INVOICE"
    AMBIGUOUS_CANDIDATE = "AMBIGUOUS_CANDIDATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    MISSING_SETTLEMENT = "MISSING_SETTLEMENT"


class ResolutionClass(str, Enum):
    """Classification of how the case is expected to be resolved."""

    AUTO_RESOLVED = "AUTO_RESOLVED"
    DETERMINISTIC_ESCALATION = "DETERMINISTIC_ESCALATION"
    AI_INVESTIGATION = "AI_INVESTIGATION"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"


class ExpectedOutcome(str, Enum):
    """Expected outcome state of the reconciliation."""

    MATCHED = "MATCHED"
    DISCREPANCY_FOUND = "DISCREPANCY_FOUND"
    UNMATCHED = "UNMATCHED"
    ADJUSTED = "ADJUSTED"


class ConfidenceBand(str, Enum):
    """Expected confidence level in the reconciliation decision."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


# ============================================================================
# DATA SCHEMAS (DATACLASSES)
# ============================================================================


@dataclass
class OrderRecord:
    order_id: str
    customer_id: str
    amount: float
    currency: str
    created_at: str
    status: str


@dataclass
class PaymentRecord:
    payment_id: str
    order_id: str
    amount: float
    method: str
    utr: str | None
    created_at: str
    status: str


@dataclass
class SettlementRecord:
    settlement_id: str
    utr: str
    amount: float
    fees: float
    settled_at: str


@dataclass
class InvoiceRecord:
    invoice_id: str
    order_id: str
    amount: float
    tax_lines_json: str
    created_at: str


@dataclass
class AdjustmentRecord:
    adjustment_id: str
    related_id: str
    type: str
    amount: float
    reason: str | None
    created_at: str


@dataclass
class GroundTruthRecord:
    ground_truth_id: str
    order_id: str
    expected_scenario: str
    expected_outcome: str
    expected_resolution_class: str
    expected_root_cause: str
    expected_human_escalation: bool
    expected_ai_investigation: bool
    expected_confidence_band: str
    expected_financial_impact: float
    notes: str


# ============================================================================
# DATA GENERATOR IMPLEMENTATION
# ============================================================================


class ReconciliationDataGenerator:
    """Deterministic generator for synthetic reconciliation data and ground truth."""

    def __init__(
        self,
        seed: int = DEFAULT_SEED,
        total_cases: int = DEFAULT_TOTAL_CASES,
        anchor_datetime: datetime = DEFAULT_ANCHOR_DATETIME,
    ):
        self.seed = seed
        self.total_cases = total_cases
        self.anchor_datetime = anchor_datetime
        self.rng = random.Random(self.seed)

        # Output collections
        self.orders: list[OrderRecord] = []
        self.payments: list[PaymentRecord] = []
        self.settlements: list[SettlementRecord] = []
        self.invoices: list[InvoiceRecord] = []
        self.adjustments: list[AdjustmentRecord] = []
        self.ground_truth: list[GroundTruthRecord] = []

        # Tracking counters
        self._case_counter = 0
        self._payment_counter = 0
        self._settlement_counter = 0
        self._invoice_counter = 0
        self._adjustment_counter = 0

    def _calc_fee(self, amount: float) -> float:
        """Calculate standard 2.0% gateway fee rounded to 2 decimals."""
        return round(amount * 0.02, 2)

    def _calc_tax_lines(self, amount: float) -> str:
        """Calculate 18% GST tax breakdown lines in JSON."""
        base_amount = round(amount / 1.18, 2)
        total_tax = round(amount - base_amount, 2)
        cgst = round(total_tax / 2, 2)
        sgst = round(total_tax - cgst, 2)
        tax_dict = {
            "base_amount": base_amount,
            "cgst": cgst,
            "sgst": sgst,
            "igst": 0.0,
            "tax_rate": 0.18,
        }
        return json.dumps(tax_dict, separators=(",", ":"))

    def _format_time(self, dt: datetime) -> str:
        """Format datetime in ISO 8601 with UTC timezone."""
        return dt.isoformat()

    def generate_all(self) -> dict[str, Any]:
        """Generate all scenarios to reach the exact target distribution."""
        # Reset state
        self.rng = random.Random(self.seed)
        self.orders.clear()
        self.payments.clear()
        self.settlements.clear()
        self.invoices.clear()
        self.adjustments.clear()
        self.ground_truth.clear()
        self._case_counter = 0
        self._payment_counter = 0
        self._settlement_counter = 0
        self._invoice_counter = 0
        self._adjustment_counter = 0

        # Scenario distribution for 1,000 cases:
        # Group 1: Deterministic Resolution (~78% -> 780 cases)
        # - EXACT_MATCH: 720 cases
        # - MULTI_ORDER_SETTLEMENT: 60 cases (20 batches of 3 orders)
        # Group 2: Deterministic Escalation (~12% -> 120 cases)
        # - AMOUNT_MISMATCH: 30 cases
        # - DELAYED_SETTLEMENT: 30 cases
        # - MISSING_PAYMENT: 30 cases
        # - CHARGEBACK_ADJUSTMENT: 30 cases
        # Group 3: AI Investigation (~10% -> 100 cases)
        # Group 3A: AI-Resolvable (50 cases)
        # - ROUNDING_MISMATCH: 20 cases
        # - REFERENCE_TYPO: 20 cases
        # - MISSING_INVOICE: 10 cases
        # Group 3B: AI-Escalation (50 cases)
        # - AMBIGUOUS_CANDIDATE: 20 cases
        # - INSUFFICIENT_EVIDENCE: 20 cases
        # - MISSING_SETTLEMENT: 10 cases

        # 1. Deterministic Resolution
        self._generate_exact_matches(720)
        self._generate_multi_order_settlements(60, batch_size=3)

        # 2. Deterministic Escalation
        self._generate_amount_mismatches(30)
        self._generate_delayed_settlements(30)
        self._generate_missing_payments(30)
        self._generate_chargeback_adjustments(30)

        # 3A. AI-Resolvable
        self._generate_rounding_mismatches(20)
        self._generate_reference_typos(20)
        self._generate_missing_invoices(10)

        # 3B. AI-Escalation
        self._generate_ambiguous_candidates(20)
        self._generate_insufficient_evidence(20)
        self._generate_missing_settlements(10)

        # Ensure ground truth is sorted by case ID
        self.ground_truth.sort(key=lambda x: x.ground_truth_id)

        return self.get_summary()

    # ------------------------------------------------------------------------
    # SCENARIO GENERATORS
    # ------------------------------------------------------------------------

    def _generate_exact_matches(self, count: int):
        """Scenario 1: Exact 1:1 clean reconciliation."""
        for i in range(count):
            self._case_counter += 1
            idx = self._case_counter
            order_id = f"ORD-{idx:06d}"
            gt_id = f"GT-{idx:06d}"
            customer_id = f"CUST-{(idx % 150) + 1:04d}"
            amount = self.rng.choice(REALISTIC_AMOUNTS)
            method = self.rng.choice(PAYMENT_METHODS)

            # Dates
            day_offset = (idx * 7) % 25
            hour_offset = (idx * 3) % 24
            min_offset = (idx * 17) % 60
            order_dt = self.anchor_datetime + timedelta(
                days=day_offset, hours=hour_offset, minutes=min_offset
            )
            pay_dt = order_dt + timedelta(minutes=self.rng.randint(2, 10))
            inv_dt = order_dt + timedelta(minutes=1)
            settle_dt = pay_dt + timedelta(days=1, hours=4)  # Normal SLA: T+1

            utr = f"UTR-IND-{idx:08d}"
            fee = self._calc_fee(amount)
            settle_amount = round(amount - fee, 2)

            # Order
            self.orders.append(
                OrderRecord(
                    order_id=order_id,
                    customer_id=customer_id,
                    amount=amount,
                    currency="INR",
                    created_at=self._format_time(order_dt),
                    status="COMPLETED",
                )
            )

            # Payment
            self._payment_counter += 1
            pay_id = f"PAY-{self._payment_counter:06d}"
            self.payments.append(
                PaymentRecord(
                    payment_id=pay_id,
                    order_id=order_id,
                    amount=amount,
                    method=method,
                    utr=utr,
                    created_at=self._format_time(pay_dt),
                    status="SUCCESS",
                )
            )

            # Settlement
            self._settlement_counter += 1
            settle_id = f"SET-{self._settlement_counter:06d}"
            self.settlements.append(
                SettlementRecord(
                    settlement_id=settle_id,
                    utr=utr,
                    amount=settle_amount,
                    fees=fee,
                    settled_at=self._format_time(settle_dt),
                )
            )

            # Invoice
            self._invoice_counter += 1
            inv_id = f"INV-{self._invoice_counter:06d}"
            self.invoices.append(
                InvoiceRecord(
                    invoice_id=inv_id,
                    order_id=order_id,
                    amount=amount,
                    tax_lines_json=self._calc_tax_lines(amount),
                    created_at=self._format_time(inv_dt),
                )
            )

            # Ground Truth
            self.ground_truth.append(
                GroundTruthRecord(
                    ground_truth_id=gt_id,
                    order_id=order_id,
                    expected_scenario=ScenarioType.EXACT_MATCH.value,
                    expected_outcome=ExpectedOutcome.MATCHED.value,
                    expected_resolution_class=ResolutionClass.AUTO_RESOLVED.value,
                    expected_root_cause="EXACT_1TO1_MATCH_VERIFIED",
                    expected_human_escalation=False,
                    expected_ai_investigation=False,
                    expected_confidence_band=ConfidenceBand.HIGH.value,
                    expected_financial_impact=0.0,
                    notes="Standard exact 1:1 match across order, payment, settlement, and invoice within T+1 SLA.",
                )
            )

    def _generate_multi_order_settlements(self, count: int, batch_size: int = 3):
        """Scenario 12: Multi-order settlement batches."""
        num_batches = count // batch_size
        for b in range(num_batches):
            batch_num = b + 1
            batch_utr = f"UTR-BATCH-{batch_num:04d}"
            batch_orders: list[tuple[str, str, float, datetime, datetime]] = []
            total_batch_amount = 0.0
            total_batch_fees = 0.0

            # Generate individual orders and payments in this batch
            for _ in range(batch_size):
                self._case_counter += 1
                idx = self._case_counter
                order_id = f"ORD-{idx:06d}"
                gt_id = f"GT-{idx:06d}"
                customer_id = f"CUST-{(idx % 150) + 1:04d}"
                amount = self.rng.choice(REALISTIC_AMOUNTS)
                method = self.rng.choice(PAYMENT_METHODS)
                fee = self._calc_fee(amount)
                total_batch_amount += amount
                total_batch_fees += fee

                day_offset = (idx * 5) % 25
                order_dt = self.anchor_datetime + timedelta(
                    days=day_offset, hours=10, minutes=15
                )
                pay_dt = order_dt + timedelta(minutes=5)
                inv_dt = order_dt + timedelta(minutes=1)

                # Order
                self.orders.append(
                    OrderRecord(
                        order_id=order_id,
                        customer_id=customer_id,
                        amount=amount,
                        currency="INR",
                        created_at=self._format_time(order_dt),
                        status="COMPLETED",
                    )
                )

                # Payment sharing batch UTR
                self._payment_counter += 1
                pay_id = f"PAY-{self._payment_counter:06d}"
                self.payments.append(
                    PaymentRecord(
                        payment_id=pay_id,
                        order_id=order_id,
                        amount=amount,
                        method=method,
                        utr=batch_utr,
                        created_at=self._format_time(pay_dt),
                        status="SUCCESS",
                    )
                )

                # Invoice
                self._invoice_counter += 1
                inv_id = f"INV-{self._invoice_counter:06d}"
                self.invoices.append(
                    InvoiceRecord(
                        invoice_id=inv_id,
                        order_id=order_id,
                        amount=amount,
                        tax_lines_json=self._calc_tax_lines(amount),
                        created_at=self._format_time(inv_dt),
                    )
                )

                # Ground Truth for each order in the batch
                self.ground_truth.append(
                    GroundTruthRecord(
                        ground_truth_id=gt_id,
                        order_id=order_id,
                        expected_scenario=ScenarioType.MULTI_ORDER_SETTLEMENT.value,
                        expected_outcome=ExpectedOutcome.MATCHED.value,
                        expected_resolution_class=ResolutionClass.AUTO_RESOLVED.value,
                        expected_root_cause="MULTI_ORDER_BATCH_SETTLEMENT_RECONCILED",
                        expected_human_escalation=False,
                        expected_ai_investigation=False,
                        expected_confidence_band=ConfidenceBand.HIGH.value,
                        expected_financial_impact=0.0,
                        notes=f"Order reconciled as part of multi-order settlement batch {batch_utr}.",
                    )
                )

                batch_orders.append((order_id, pay_id, amount, order_dt, pay_dt))

            # Single aggregated Settlement for the entire batch
            self._settlement_counter += 1
            settle_id = f"SET-BATCH-{batch_num:04d}"
            batch_settle_dt = max(p[4] for p in batch_orders) + timedelta(
                days=1, hours=2
            )
            net_settle_amount = round(total_batch_amount - total_batch_fees, 2)

            self.settlements.append(
                SettlementRecord(
                    settlement_id=settle_id,
                    utr=batch_utr,
                    amount=net_settle_amount,
                    fees=round(total_batch_fees, 2),
                    settled_at=self._format_time(batch_settle_dt),
                )
            )

    def _generate_amount_mismatches(self, count: int):
        """Scenario 2: Significant amount mismatch between order and payment."""
        for _ in range(count):
            self._case_counter += 1
            idx = self._case_counter
            order_id = f"ORD-{idx:06d}"
            gt_id = f"GT-{idx:06d}"
            customer_id = f"CUST-{(idx % 150) + 1:04d}"
            order_amount = 4999.00
            payment_amount = 3499.00  # Noticeable mismatch
            diff = round(abs(order_amount - payment_amount), 2)
            method = "UPI"

            order_dt = self.anchor_datetime + timedelta(
                days=(idx * 2) % 25, hours=14, minutes=20
            )
            pay_dt = order_dt + timedelta(minutes=5)
            inv_dt = order_dt + timedelta(minutes=1)
            settle_dt = pay_dt + timedelta(days=1)
            utr = f"UTR-IND-{idx:08d}"
            fee = self._calc_fee(payment_amount)

            self.orders.append(
                OrderRecord(
                    order_id=order_id,
                    customer_id=customer_id,
                    amount=order_amount,
                    currency="INR",
                    created_at=self._format_time(order_dt),
                    status="COMPLETED",
                )
            )
            self._payment_counter += 1
            pay_id = f"PAY-{self._payment_counter:06d}"
            self.payments.append(
                PaymentRecord(
                    payment_id=pay_id,
                    order_id=order_id,
                    amount=payment_amount,
                    method=method,
                    utr=utr,
                    created_at=self._format_time(pay_dt),
                    status="SUCCESS",
                )
            )
            self._settlement_counter += 1
            settle_id = f"SET-{self._settlement_counter:06d}"
            self.settlements.append(
                SettlementRecord(
                    settlement_id=settle_id,
                    utr=utr,
                    amount=round(payment_amount - fee, 2),
                    fees=fee,
                    settled_at=self._format_time(settle_dt),
                )
            )
            self._invoice_counter += 1
            inv_id = f"INV-{self._invoice_counter:06d}"
            self.invoices.append(
                InvoiceRecord(
                    invoice_id=inv_id,
                    order_id=order_id,
                    amount=order_amount,
                    tax_lines_json=self._calc_tax_lines(order_amount),
                    created_at=self._format_time(inv_dt),
                )
            )

            self.ground_truth.append(
                GroundTruthRecord(
                    ground_truth_id=gt_id,
                    order_id=order_id,
                    expected_scenario=ScenarioType.AMOUNT_MISMATCH.value,
                    expected_outcome=ExpectedOutcome.DISCREPANCY_FOUND.value,
                    expected_resolution_class=ResolutionClass.DETERMINISTIC_ESCALATION.value,
                    expected_root_cause="PAYMENT_AMOUNT_MISMATCH_EXCEEDS_TOLERANCE",
                    expected_human_escalation=True,
                    expected_ai_investigation=False,
                    expected_confidence_band=ConfidenceBand.HIGH.value,
                    expected_financial_impact=diff,
                    notes=f"Order amount INR {order_amount} does not match captured payment INR {payment_amount}.",
                )
            )

    def _generate_delayed_settlements(self, count: int):
        """Scenario 4: Settlement exceeds maximum SLA window (> 5 business days)."""
        for _ in range(count):
            self._case_counter += 1
            idx = self._case_counter
            order_id = f"ORD-{idx:06d}"
            gt_id = f"GT-{idx:06d}"
            customer_id = f"CUST-{(idx % 150) + 1:04d}"
            amount = self.rng.choice(REALISTIC_AMOUNTS)
            method = "NETBANKING"

            order_dt = self.anchor_datetime + timedelta(
                days=(idx % 10), hours=11, minutes=10
            )
            pay_dt = order_dt + timedelta(minutes=15)
            inv_dt = order_dt + timedelta(minutes=1)
            settle_dt = pay_dt + timedelta(days=7, hours=14)  # 7 days delayed (> 5 day SLA)
            utr = f"UTR-IND-{idx:08d}"
            fee = self._calc_fee(amount)

            self.orders.append(
                OrderRecord(
                    order_id=order_id,
                    customer_id=customer_id,
                    amount=amount,
                    currency="INR",
                    created_at=self._format_time(order_dt),
                    status="COMPLETED",
                )
            )
            self._payment_counter += 1
            pay_id = f"PAY-{self._payment_counter:06d}"
            self.payments.append(
                PaymentRecord(
                    payment_id=pay_id,
                    order_id=order_id,
                    amount=amount,
                    method=method,
                    utr=utr,
                    created_at=self._format_time(pay_dt),
                    status="SUCCESS",
                )
            )
            self._settlement_counter += 1
            settle_id = f"SET-{self._settlement_counter:06d}"
            self.settlements.append(
                SettlementRecord(
                    settlement_id=settle_id,
                    utr=utr,
                    amount=round(amount - fee, 2),
                    fees=fee,
                    settled_at=self._format_time(settle_dt),
                )
            )
            self._invoice_counter += 1
            inv_id = f"INV-{self._invoice_counter:06d}"
            self.invoices.append(
                InvoiceRecord(
                    invoice_id=inv_id,
                    order_id=order_id,
                    amount=amount,
                    tax_lines_json=self._calc_tax_lines(amount),
                    created_at=self._format_time(inv_dt),
                )
            )

            self.ground_truth.append(
                GroundTruthRecord(
                    ground_truth_id=gt_id,
                    order_id=order_id,
                    expected_scenario=ScenarioType.DELAYED_SETTLEMENT.value,
                    expected_outcome=ExpectedOutcome.DISCREPANCY_FOUND.value,
                    expected_resolution_class=ResolutionClass.DETERMINISTIC_ESCALATION.value,
                    expected_root_cause="SETTLEMENT_DELAY_EXCEEDS_SLA_POLICY",
                    expected_human_escalation=True,
                    expected_ai_investigation=False,
                    expected_confidence_band=ConfidenceBand.HIGH.value,
                    expected_financial_impact=0.0,
                    notes="Bank settlement completed 7 days after payment, exceeding policy SLA limit of 5 days.",
                )
            )

    def _generate_missing_payments(self, count: int):
        """Scenario 6: Order fulfilled in merchant system but payment record missing."""
        for _ in range(count):
            self._case_counter += 1
            idx = self._case_counter
            order_id = f"ORD-{idx:06d}"
            gt_id = f"GT-{idx:06d}"
            customer_id = f"CUST-{(idx % 150) + 1:04d}"
            amount = self.rng.choice(REALISTIC_AMOUNTS)

            order_dt = self.anchor_datetime + timedelta(
                days=(idx * 3) % 25, hours=9, minutes=45
            )
            inv_dt = order_dt + timedelta(minutes=1)

            # Order exists & invoice generated, but NO payment or settlement was captured
            self.orders.append(
                OrderRecord(
                    order_id=order_id,
                    customer_id=customer_id,
                    amount=amount,
                    currency="INR",
                    created_at=self._format_time(order_dt),
                    status="COMPLETED",
                )
            )
            self._invoice_counter += 1
            inv_id = f"INV-{self._invoice_counter:06d}"
            self.invoices.append(
                InvoiceRecord(
                    invoice_id=inv_id,
                    order_id=order_id,
                    amount=amount,
                    tax_lines_json=self._calc_tax_lines(amount),
                    created_at=self._format_time(inv_dt),
                )
            )

            self.ground_truth.append(
                GroundTruthRecord(
                    ground_truth_id=gt_id,
                    order_id=order_id,
                    expected_scenario=ScenarioType.MISSING_PAYMENT.value,
                    expected_outcome=ExpectedOutcome.UNMATCHED.value,
                    expected_resolution_class=ResolutionClass.DETERMINISTIC_ESCALATION.value,
                    expected_root_cause="ORDER_FULFILLED_WITHOUT_GATEWAY_PAYMENT",
                    expected_human_escalation=True,
                    expected_ai_investigation=False,
                    expected_confidence_band=ConfidenceBand.HIGH.value,
                    expected_financial_impact=amount,
                    notes="Merchant order completed with invoice but zero payment captured from gateway.",
                )
            )

    def _generate_chargeback_adjustments(self, count: int):
        """Scenario 8: Chargeback or clawback adjustment applied to payment."""
        for _ in range(count):
            self._case_counter += 1
            idx = self._case_counter
            order_id = f"ORD-{idx:06d}"
            gt_id = f"GT-{idx:06d}"
            customer_id = f"CUST-{(idx % 150) + 1:04d}"
            amount = self.rng.choice(REALISTIC_AMOUNTS)
            method = "CARD"

            order_dt = self.anchor_datetime + timedelta(
                days=(idx * 4) % 20, hours=16, minutes=30
            )
            pay_dt = order_dt + timedelta(minutes=5)
            inv_dt = order_dt + timedelta(minutes=1)
            settle_dt = pay_dt + timedelta(days=1)
            adj_dt = pay_dt + timedelta(days=4)
            utr = f"UTR-IND-{idx:08d}"
            fee = self._calc_fee(amount)

            self.orders.append(
                OrderRecord(
                    order_id=order_id,
                    customer_id=customer_id,
                    amount=amount,
                    currency="INR",
                    created_at=self._format_time(order_dt),
                    status="COMPLETED",
                )
            )
            self._payment_counter += 1
            pay_id = f"PAY-{self._payment_counter:06d}"
            self.payments.append(
                PaymentRecord(
                    payment_id=pay_id,
                    order_id=order_id,
                    amount=amount,
                    method=method,
                    utr=utr,
                    created_at=self._format_time(pay_dt),
                    status="SUCCESS",
                )
            )
            self._settlement_counter += 1
            settle_id = f"SET-{self._settlement_counter:06d}"
            self.settlements.append(
                SettlementRecord(
                    settlement_id=settle_id,
                    utr=utr,
                    amount=round(amount - fee, 2),
                    fees=fee,
                    settled_at=self._format_time(settle_dt),
                )
            )
            self._invoice_counter += 1
            inv_id = f"INV-{self._invoice_counter:06d}"
            self.invoices.append(
                InvoiceRecord(
                    invoice_id=inv_id,
                    order_id=order_id,
                    amount=amount,
                    tax_lines_json=self._calc_tax_lines(amount),
                    created_at=self._format_time(inv_dt),
                )
            )

            # Adjustment record
            self._adjustment_counter += 1
            adj_id = f"ADJ-{self._adjustment_counter:06d}"
            self.adjustments.append(
                AdjustmentRecord(
                    adjustment_id=adj_id,
                    related_id=pay_id,
                    type="CHARGEBACK",
                    amount=-amount,
                    reason="Customer bank dispute: unauthorized transaction chargeback",
                    created_at=self._format_time(adj_dt),
                )
            )

            self.ground_truth.append(
                GroundTruthRecord(
                    ground_truth_id=gt_id,
                    order_id=order_id,
                    expected_scenario=ScenarioType.CHARGEBACK_ADJUSTMENT.value,
                    expected_outcome=ExpectedOutcome.ADJUSTED.value,
                    expected_resolution_class=ResolutionClass.DETERMINISTIC_ESCALATION.value,
                    expected_root_cause="UNRESOLVED_CHARGEBACK_DISPUTE_REQUIRES_HUMAN",
                    expected_human_escalation=True,
                    expected_ai_investigation=False,
                    expected_confidence_band=ConfidenceBand.HIGH.value,
                    expected_financial_impact=amount,
                    notes=f"Chargeback adjustment of INR {amount} logged for payment {pay_id}.",
                )
            )

    def _generate_rounding_mismatches(self, count: int):
        """Scenario 3: Fractional rounding mismatch (< INR 1.00) AI can resolve."""
        for _ in range(count):
            self._case_counter += 1
            idx = self._case_counter
            order_id = f"ORD-{idx:06d}"
            gt_id = f"GT-{idx:06d}"
            customer_id = f"CUST-{(idx % 150) + 1:04d}"
            order_amount = 1499.50
            diff = 0.05
            payment_amount = round(order_amount + diff, 2)
            method = "UPI"

            order_dt = self.anchor_datetime + timedelta(
                days=(idx * 2) % 25, hours=12, minutes=0
            )
            pay_dt = order_dt + timedelta(minutes=5)
            inv_dt = order_dt + timedelta(minutes=1)
            settle_dt = pay_dt + timedelta(days=1)
            utr = f"UTR-IND-{idx:08d}"
            fee = self._calc_fee(payment_amount)

            self.orders.append(
                OrderRecord(
                    order_id=order_id,
                    customer_id=customer_id,
                    amount=order_amount,
                    currency="INR",
                    created_at=self._format_time(order_dt),
                    status="COMPLETED",
                )
            )
            self._payment_counter += 1
            pay_id = f"PAY-{self._payment_counter:06d}"
            self.payments.append(
                PaymentRecord(
                    payment_id=pay_id,
                    order_id=order_id,
                    amount=payment_amount,
                    method=method,
                    utr=utr,
                    created_at=self._format_time(pay_dt),
                    status="SUCCESS",
                )
            )
            self._settlement_counter += 1
            settle_id = f"SET-{self._settlement_counter:06d}"
            self.settlements.append(
                SettlementRecord(
                    settlement_id=settle_id,
                    utr=utr,
                    amount=round(payment_amount - fee, 2),
                    fees=fee,
                    settled_at=self._format_time(settle_dt),
                )
            )
            self._invoice_counter += 1
            inv_id = f"INV-{self._invoice_counter:06d}"
            self.invoices.append(
                InvoiceRecord(
                    invoice_id=inv_id,
                    order_id=order_id,
                    amount=order_amount,
                    tax_lines_json=self._calc_tax_lines(order_amount),
                    created_at=self._format_time(inv_dt),
                )
            )

            # AI-Resolvable ground truth
            self.ground_truth.append(
                GroundTruthRecord(
                    ground_truth_id=gt_id,
                    order_id=order_id,
                    expected_scenario=ScenarioType.ROUNDING_MISMATCH.value,
                    expected_outcome=ExpectedOutcome.DISCREPANCY_FOUND.value,
                    expected_resolution_class=ResolutionClass.AI_INVESTIGATION.value,
                    expected_root_cause="TAX_LINE_ROUNDING_DISCREPANCY_AI_EXPLAINABLE",
                    expected_human_escalation=False,
                    expected_ai_investigation=True,
                    expected_confidence_band=ConfidenceBand.HIGH.value,
                    expected_financial_impact=diff,
                    notes="Micro-discrepancy (INR 0.05) caused by itemized GST line rounding; AI can verify invoice tax lines.",
                )
            )

    def _generate_reference_typos(self, count: int):
        """Scenario 9: Gateway UTR 1-character typo; AI fuzzy-matchable."""
        for _ in range(count):
            self._case_counter += 1
            idx = self._case_counter
            order_id = f"ORD-{idx:06d}"
            gt_id = f"GT-{idx:06d}"
            customer_id = f"CUST-{(idx % 150) + 1:04d}"
            amount = self.rng.choice(REALISTIC_AMOUNTS)
            method = "UPI"

            order_dt = self.anchor_datetime + timedelta(
                days=(idx * 3) % 25, hours=15, minutes=30
            )
            pay_dt = order_dt + timedelta(minutes=5)
            inv_dt = order_dt + timedelta(minutes=1)
            settle_dt = pay_dt + timedelta(days=1)

            # UTR with transposed digits in settlement record
            pay_utr = f"UTR-IND-{idx:06d}12"
            settle_utr = f"UTR-IND-{idx:06d}21"  # 12 vs 21 transposition
            fee = self._calc_fee(amount)

            self.orders.append(
                OrderRecord(
                    order_id=order_id,
                    customer_id=customer_id,
                    amount=amount,
                    currency="INR",
                    created_at=self._format_time(order_dt),
                    status="COMPLETED",
                )
            )
            self._payment_counter += 1
            pay_id = f"PAY-{self._payment_counter:06d}"
            self.payments.append(
                PaymentRecord(
                    payment_id=pay_id,
                    order_id=order_id,
                    amount=amount,
                    method=method,
                    utr=pay_utr,
                    created_at=self._format_time(pay_dt),
                    status="SUCCESS",
                )
            )
            self._settlement_counter += 1
            settle_id = f"SET-{self._settlement_counter:06d}"
            self.settlements.append(
                SettlementRecord(
                    settlement_id=settle_id,
                    utr=settle_utr,
                    amount=round(amount - fee, 2),
                    fees=fee,
                    settled_at=self._format_time(settle_dt),
                )
            )
            self._invoice_counter += 1
            inv_id = f"INV-{self._invoice_counter:06d}"
            self.invoices.append(
                InvoiceRecord(
                    invoice_id=inv_id,
                    order_id=order_id,
                    amount=amount,
                    tax_lines_json=self._calc_tax_lines(amount),
                    created_at=self._format_time(inv_dt),
                )
            )

            # AI-Resolvable ground truth
            self.ground_truth.append(
                GroundTruthRecord(
                    ground_truth_id=gt_id,
                    order_id=order_id,
                    expected_scenario=ScenarioType.REFERENCE_TYPO.value,
                    expected_outcome=ExpectedOutcome.DISCREPANCY_FOUND.value,
                    expected_resolution_class=ResolutionClass.AI_INVESTIGATION.value,
                    expected_root_cause="SETTLEMENT_UTR_TYPO_FUZZY_MATCHABLE",
                    expected_human_escalation=False,
                    expected_ai_investigation=True,
                    expected_confidence_band=ConfidenceBand.MEDIUM.value,
                    expected_financial_impact=0.0,
                    notes=f"Bank settlement UTR has transposed characters ({settle_utr} vs {pay_utr}); AI can reconstruct 1:1 match.",
                )
            )

    def _generate_missing_invoices(self, count: int):
        """Scenario 5: Missing invoice record (generation dropped) AI can resolve."""
        for _ in range(count):
            self._case_counter += 1
            idx = self._case_counter
            order_id = f"ORD-{idx:06d}"
            gt_id = f"GT-{idx:06d}"
            customer_id = f"CUST-{(idx % 150) + 1:04d}"
            amount = self.rng.choice(REALISTIC_AMOUNTS)
            method = "CARD"

            order_dt = self.anchor_datetime + timedelta(
                days=(idx * 4) % 25, hours=8, minutes=10
            )
            pay_dt = order_dt + timedelta(minutes=5)
            settle_dt = pay_dt + timedelta(days=1)
            utr = f"UTR-IND-{idx:08d}"
            fee = self._calc_fee(amount)

            self.orders.append(
                OrderRecord(
                    order_id=order_id,
                    customer_id=customer_id,
                    amount=amount,
                    currency="INR",
                    created_at=self._format_time(order_dt),
                    status="COMPLETED",
                )
            )
            self._payment_counter += 1
            pay_id = f"PAY-{self._payment_counter:06d}"
            self.payments.append(
                PaymentRecord(
                    payment_id=pay_id,
                    order_id=order_id,
                    amount=amount,
                    method=method,
                    utr=utr,
                    created_at=self._format_time(pay_dt),
                    status="SUCCESS",
                )
            )
            self._settlement_counter += 1
            settle_id = f"SET-{self._settlement_counter:06d}"
            self.settlements.append(
                SettlementRecord(
                    settlement_id=settle_id,
                    utr=utr,
                    amount=round(amount - fee, 2),
                    fees=fee,
                    settled_at=self._format_time(settle_dt),
                )
            )
            # Invoice record omitted intentionally

            # AI-Resolvable ground truth
            self.ground_truth.append(
                GroundTruthRecord(
                    ground_truth_id=gt_id,
                    order_id=order_id,
                    expected_scenario=ScenarioType.MISSING_INVOICE.value,
                    expected_outcome=ExpectedOutcome.DISCREPANCY_FOUND.value,
                    expected_resolution_class=ResolutionClass.AI_INVESTIGATION.value,
                    expected_root_cause="MISSING_INVOICE_ORDER_PAYMENT_VERIFIED",
                    expected_human_escalation=False,
                    expected_ai_investigation=True,
                    expected_confidence_band=ConfidenceBand.HIGH.value,
                    expected_financial_impact=0.0,
                    notes="Payment and settlement matched; invoice dropped by billing worker; AI can confirm validity for backfill.",
                )
            )

    def _generate_ambiguous_candidates(self, count: int):
        """Scenario 10: Multiple candidate payments for same customer/amount (AI-Escalation)."""
        for _ in range(count):
            self._case_counter += 1
            idx = self._case_counter
            order_id = f"ORD-{idx:06d}"
            gt_id = f"GT-{idx:06d}"
            customer_id = f"CUST-{(idx % 150) + 1:04d}"
            amount = 2499.00
            method = "UPI"

            order_dt = self.anchor_datetime + timedelta(
                days=(idx * 2) % 25, hours=18, minutes=20
            )
            pay_dt1 = order_dt + timedelta(minutes=2)
            pay_dt2 = order_dt + timedelta(minutes=4)  # Duplicate retry attempt
            inv_dt = order_dt + timedelta(minutes=1)
            settle_dt = pay_dt1 + timedelta(days=1)
            utr1 = f"UTR-IND-{idx:06d}A"
            utr2 = f"UTR-IND-{idx:06d}B"
            fee = self._calc_fee(amount)

            self.orders.append(
                OrderRecord(
                    order_id=order_id,
                    customer_id=customer_id,
                    amount=amount,
                    currency="INR",
                    created_at=self._format_time(order_dt),
                    status="COMPLETED",
                )
            )
            # Candidate 1
            self._payment_counter += 1
            pay_id1 = f"PAY-{self._payment_counter:06d}"
            self.payments.append(
                PaymentRecord(
                    payment_id=pay_id1,
                    order_id=order_id,
                    amount=amount,
                    method=method,
                    utr=utr1,
                    created_at=self._format_time(pay_dt1),
                    status="SUCCESS",
                )
            )
            # Candidate 2 (Retry attempt with same order_id)
            self._payment_counter += 1
            pay_id2 = f"PAY-{self._payment_counter:06d}"
            self.payments.append(
                PaymentRecord(
                    payment_id=pay_id2,
                    order_id=order_id,
                    amount=amount,
                    method=method,
                    utr=utr2,
                    created_at=self._format_time(pay_dt2),
                    status="SUCCESS",
                )
            )
            # Single settlement exists
            self._settlement_counter += 1
            settle_id = f"SET-{self._settlement_counter:06d}"
            self.settlements.append(
                SettlementRecord(
                    settlement_id=settle_id,
                    utr=utr1,
                    amount=round(amount - fee, 2),
                    fees=fee,
                    settled_at=self._format_time(settle_dt),
                )
            )
            self._invoice_counter += 1
            inv_id = f"INV-{self._invoice_counter:06d}"
            self.invoices.append(
                InvoiceRecord(
                    invoice_id=inv_id,
                    order_id=order_id,
                    amount=amount,
                    tax_lines_json=self._calc_tax_lines(amount),
                    created_at=self._format_time(inv_dt),
                )
            )

            # AI-Escalation ground truth ("AI knows when it doesn't know")
            self.ground_truth.append(
                GroundTruthRecord(
                    ground_truth_id=gt_id,
                    order_id=order_id,
                    expected_scenario=ScenarioType.AMBIGUOUS_CANDIDATE.value,
                    expected_outcome=ExpectedOutcome.DISCREPANCY_FOUND.value,
                    expected_resolution_class=ResolutionClass.AI_INVESTIGATION.value,
                    expected_root_cause="DUPLICATE_CANDIDATE_PAYMENTS_REQUIRE_HUMAN_OPS",
                    expected_human_escalation=True,
                    expected_ai_investigation=True,
                    expected_confidence_band=ConfidenceBand.LOW.value,
                    expected_financial_impact=amount,
                    notes=f"Two successful gateway payments ({pay_id1}, {pay_id2}) exist for same order; AI must escalate to ops.",
                )
            )

    def _generate_insufficient_evidence(self, count: int):
        """Scenario 11: Genuine insufficient evidence with ambiguous manual adjustment."""
        for _ in range(count):
            self._case_counter += 1
            idx = self._case_counter
            order_id = f"ORD-{idx:06d}"
            gt_id = f"GT-{idx:06d}"
            customer_id = f"CUST-{(idx % 150) + 1:04d}"
            amount = 9999.00

            order_dt = self.anchor_datetime + timedelta(
                days=(idx * 5) % 25, hours=20, minutes=45
            )
            adj_dt = order_dt + timedelta(days=2)

            self.orders.append(
                OrderRecord(
                    order_id=order_id,
                    customer_id=customer_id,
                    amount=amount,
                    currency="INR",
                    created_at=self._format_time(order_dt),
                    status="ABANDONED",
                )
            )
            # Unlinked generic adjustment with zero gateway metadata
            self._adjustment_counter += 1
            adj_id = f"ADJ-{self._adjustment_counter:06d}"
            self.adjustments.append(
                AdjustmentRecord(
                    adjustment_id=adj_id,
                    related_id=order_id,
                    type="DISPUTE_FEE",
                    amount=-250.00,
                    reason="Manual ledger correction #994 without reference trace",
                    created_at=self._format_time(adj_dt),
                )
            )

            # AI-Escalation ground truth
            self.ground_truth.append(
                GroundTruthRecord(
                    ground_truth_id=gt_id,
                    order_id=order_id,
                    expected_scenario=ScenarioType.INSUFFICIENT_EVIDENCE.value,
                    expected_outcome=ExpectedOutcome.UNMATCHED.value,
                    expected_resolution_class=ResolutionClass.AI_INVESTIGATION.value,
                    expected_root_cause="GENUINE_INSUFFICIENT_EVIDENCE_FOR_SAFE_RECON",
                    expected_human_escalation=True,
                    expected_ai_investigation=True,
                    expected_confidence_band=ConfidenceBand.NONE.value,
                    expected_financial_impact=amount,
                    notes="Abandoned order with unlinked manual debit; insufficient evidence across all sources; AI safely escalates.",
                )
            )

    def _generate_missing_settlements(self, count: int):
        """Scenario 7: Successful payment captured, settlement not found at bank."""
        for _ in range(count):
            self._case_counter += 1
            idx = self._case_counter
            order_id = f"ORD-{idx:06d}"
            gt_id = f"GT-{idx:06d}"
            customer_id = f"CUST-{(idx % 150) + 1:04d}"
            amount = self.rng.choice(REALISTIC_AMOUNTS)
            method = "UPI"

            order_dt = self.anchor_datetime + timedelta(
                days=(idx * 3) % 25, hours=10, minutes=30
            )
            pay_dt = order_dt + timedelta(minutes=5)
            inv_dt = order_dt + timedelta(minutes=1)
            utr = f"UTR-IND-{idx:08d}"

            self.orders.append(
                OrderRecord(
                    order_id=order_id,
                    customer_id=customer_id,
                    amount=amount,
                    currency="INR",
                    created_at=self._format_time(order_dt),
                    status="COMPLETED",
                )
            )
            self._payment_counter += 1
            pay_id = f"PAY-{self._payment_counter:06d}"
            self.payments.append(
                PaymentRecord(
                    payment_id=pay_id,
                    order_id=order_id,
                    amount=amount,
                    method=method,
                    utr=utr,
                    created_at=self._format_time(pay_dt),
                    status="SUCCESS",
                )
            )
            self._invoice_counter += 1
            inv_id = f"INV-{self._invoice_counter:06d}"
            self.invoices.append(
                InvoiceRecord(
                    invoice_id=inv_id,
                    order_id=order_id,
                    amount=amount,
                    tax_lines_json=self._calc_tax_lines(amount),
                    created_at=self._format_time(inv_dt),
                )
            )
            # Settlement row is intentionally omitted

            # AI-Escalation ground truth
            self.ground_truth.append(
                GroundTruthRecord(
                    ground_truth_id=gt_id,
                    order_id=order_id,
                    expected_scenario=ScenarioType.MISSING_SETTLEMENT.value,
                    expected_outcome=ExpectedOutcome.DISCREPANCY_FOUND.value,
                    expected_resolution_class=ResolutionClass.AI_INVESTIGATION.value,
                    expected_root_cause="PAYMENT_CAPTURED_SETTLEMENT_NOT_FOUND",
                    expected_human_escalation=True,
                    expected_ai_investigation=True,
                    expected_confidence_band=ConfidenceBand.MEDIUM.value,
                    expected_financial_impact=amount,
                    notes="Payment captured with UTR but settlement payout not acknowledged by bank; AI routes to banking operations.",
                )
            )

    # ------------------------------------------------------------------------
    # SUMMARY & SERIALIZATION
    # ------------------------------------------------------------------------

    def get_summary(self) -> dict[str, Any]:
        """Compute scenario counts, resolution distribution, and percentages."""
        scenario_counts: dict[str, int] = {}
        for gt in self.ground_truth:
            scenario_counts[gt.expected_scenario] = (
                scenario_counts.get(gt.expected_scenario, 0) + 1
            )

        det_resolved = sum(
            1
            for gt in self.ground_truth
            if gt.expected_resolution_class == ResolutionClass.AUTO_RESOLVED.value
        )
        det_escalated = sum(
            1
            for gt in self.ground_truth
            if gt.expected_resolution_class
            == ResolutionClass.DETERMINISTIC_ESCALATION.value
        )
        ai_investigation = sum(
            1
            for gt in self.ground_truth
            if gt.expected_resolution_class
            == ResolutionClass.AI_INVESTIGATION.value
        )

        ai_resolvable = sum(
            1
            for gt in self.ground_truth
            if gt.expected_resolution_class == ResolutionClass.AI_INVESTIGATION.value
            and not gt.expected_human_escalation
        )
        ai_escalation = sum(
            1
            for gt in self.ground_truth
            if gt.expected_resolution_class == ResolutionClass.AI_INVESTIGATION.value
            and gt.expected_human_escalation
        )

        total = len(self.ground_truth)
        pct_det_resolved = round((det_resolved / total) * 100, 2) if total else 0.0
        pct_det_escalated = round((det_escalated / total) * 100, 2) if total else 0.0
        pct_ai_investigation = (
            round((ai_investigation / total) * 100, 2) if total else 0.0
        )

        return {
            "dataset_version": DATASET_VERSION,
            "seed": self.seed,
            "anchor_datetime": self.anchor_datetime.isoformat(),
            "total_cases": total,
            "scenario_counts": scenario_counts,
            "distribution": {
                "deterministic_resolution": {
                    "count": det_resolved,
                    "percentage": pct_det_resolved,
                    "target_percentage": 78.0,
                },
                "deterministic_escalation": {
                    "count": det_escalated,
                    "percentage": pct_det_escalated,
                    "target_percentage": 12.0,
                },
                "ai_investigation": {
                    "count": ai_investigation,
                    "percentage": pct_ai_investigation,
                    "target_percentage": 10.0,
                    "ai_resolvable": {
                        "count": ai_resolvable,
                        "percentage": round((ai_resolvable / total) * 100, 2)
                        if total
                        else 0.0,
                    },
                    "ai_escalation": {
                        "count": ai_escalation,
                        "percentage": round((ai_escalation / total) * 100, 2)
                        if total
                        else 0.0,
                    },
                },
            },
            "table_record_counts": {
                "orders": len(self.orders),
                "payments": len(self.payments),
                "settlements": len(self.settlements),
                "invoices": len(self.invoices),
                "adjustments": len(self.adjustments),
                "ground_truth": len(self.ground_truth),
            },
        }

    def save_to_disk(self, base_data_dir: Path | str | None = None) -> dict[str, Path]:
        """Save generated datasets and ground-truth files to disk."""
        if base_data_dir is None:
            base_data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        else:
            base_data_dir = Path(base_data_dir)

        gen_dir = base_data_dir / "generated"
        gt_dir = base_data_dir / "ground_truth"
        raw_dir = base_data_dir / "raw"

        gen_dir.mkdir(parents=True, exist_ok=True)
        gt_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save Orders CSV
        orders_path = gen_dir / "orders.csv"
        with open(orders_path, "w", encoding="utf-8", newline="") as f:
            f.write("order_id,customer_id,amount,currency,created_at,status\n")
            for o in self.orders:
                f.write(
                    f"{o.order_id},{o.customer_id},{o.amount:.2f},{o.currency},{o.created_at},{o.status}\n"
                )

        # 2. Save Payments CSV
        payments_path = gen_dir / "payments.csv"
        with open(payments_path, "w", encoding="utf-8", newline="") as f:
            f.write("payment_id,order_id,amount,method,utr,created_at,status\n")
            for p in self.payments:
                utr_str = p.utr or ""
                f.write(
                    f"{p.payment_id},{p.order_id},{p.amount:.2f},{p.method},{utr_str},{p.created_at},{p.status}\n"
                )

        # 3. Save Settlements CSV
        settlements_path = gen_dir / "settlements.csv"
        with open(settlements_path, "w", encoding="utf-8", newline="") as f:
            f.write("settlement_id,utr,amount,fees,settled_at\n")
            for s in self.settlements:
                f.write(
                    f"{s.settlement_id},{s.utr},{s.amount:.2f},{s.fees:.2f},{s.settled_at}\n"
                )

        # 4. Save Invoices CSV
        invoices_path = gen_dir / "invoices.csv"
        with open(invoices_path, "w", encoding="utf-8", newline="") as f:
            f.write("invoice_id,order_id,amount,tax_lines_json,created_at\n")
            for inv in self.invoices:
                # Escape double quotes for CSV
                tax_escaped = inv.tax_lines_json.replace('"', '""')
                f.write(
                    f'{inv.invoice_id},{inv.order_id},{inv.amount:.2f},"{tax_escaped}",{inv.created_at}\n'
                )

        # 5. Save Adjustments CSV
        adjustments_path = gen_dir / "adjustments.csv"
        with open(adjustments_path, "w", encoding="utf-8", newline="") as f:
            f.write("adjustment_id,related_id,type,amount,reason,created_at\n")
            for adj in self.adjustments:
                reason_str = (adj.reason or "").replace('"', '""')
                f.write(
                    f'{adj.adjustment_id},{adj.related_id},{adj.type},{adj.amount:.2f},"{reason_str}",{adj.created_at}\n'
                )

        # 6. Save Ground Truth CSV
        gt_csv_path = gt_dir / "ground_truth.csv"
        with open(gt_csv_path, "w", encoding="utf-8", newline="") as f:
            f.write(
                "ground_truth_id,order_id,expected_scenario,expected_outcome,"
                "expected_resolution_class,expected_root_cause,expected_human_escalation,"
                "expected_ai_investigation,expected_confidence_band,expected_financial_impact,notes\n"
            )
            for gt in self.ground_truth:
                notes_escaped = gt.notes.replace('"', '""')
                f.write(
                    f'{gt.ground_truth_id},{gt.order_id},{gt.expected_scenario},'
                    f'{gt.expected_outcome},{gt.expected_resolution_class},'
                    f'{gt.expected_root_cause},{gt.expected_human_escalation},'
                    f'{gt.expected_ai_investigation},{gt.expected_confidence_band},'
                    f'{gt.expected_financial_impact:.2f},"{notes_escaped}"\n'
                )

        # 7. Save Ground Truth JSON
        gt_json_path = gt_dir / "ground_truth.json"
        with open(gt_json_path, "w", encoding="utf-8") as f:
            json.dump(
                [asdict(gt) for gt in self.ground_truth],
                f,
                indent=2,
                ensure_ascii=False,
            )

        # 8. Save Dataset Metadata JSON
        meta_path = gen_dir / "dataset_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.get_summary(), f, indent=2, ensure_ascii=False)

        return {
            "orders": orders_path,
            "payments": payments_path,
            "settlements": settlements_path,
            "invoices": invoices_path,
            "adjustments": adjustments_path,
            "ground_truth_csv": gt_csv_path,
            "ground_truth_json": gt_json_path,
            "metadata": meta_path,
        }


# ============================================================================
# VALIDATION LOGIC
# ============================================================================


def validate_dataset(base_data_dir: Path | str | None = None) -> tuple[bool, list[str]]:
    """Strictly validate generated dataset and ground truth for consistency, schemas, and distribution.

    Returns:
        tuple[bool, list[str]]: (is_valid, list_of_error_messages)
    """
    if base_data_dir is None:
        base_data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    else:
        base_data_dir = Path(base_data_dir)

    gen_dir = base_data_dir / "generated"
    gt_dir = base_data_dir / "ground_truth"

    errors: list[str] = []

    # 1. Required Files Exist
    required_files = [
        gen_dir / "orders.csv",
        gen_dir / "payments.csv",
        gen_dir / "settlements.csv",
        gen_dir / "invoices.csv",
        gen_dir / "adjustments.csv",
        gen_dir / "dataset_metadata.json",
        gt_dir / "ground_truth.csv",
        gt_dir / "ground_truth.json",
    ]

    for req_file in required_files:
        if not req_file.exists():
            errors.append(f"Missing required file: {req_file}")

    if errors:
        return False, errors

    # 2. Validate Metadata JSON
    try:
        with open(gen_dir / "dataset_metadata.json", encoding="utf-8") as f:
            metadata = json.load(f)
        if "seed" not in metadata or metadata["seed"] != DEFAULT_SEED:
            errors.append(f"Invalid seed in metadata: {metadata.get('seed')}")
        if "anchor_datetime" not in metadata:
            errors.append("anchor_datetime missing in metadata")
    except Exception as e:
        errors.append(f"Failed to parse dataset_metadata.json: {e}")

    # Helper CSV parser
    def parse_csv_rows(filepath: Path) -> tuple[list[str], list[dict[str, str]]]:
        import csv

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            rows = list(reader)
        return headers, rows

    # 3. Validate Orders CSV
    order_headers, orders_rows = parse_csv_rows(gen_dir / "orders.csv")
    expected_order_cols = [
        "order_id",
        "customer_id",
        "amount",
        "currency",
        "created_at",
        "status",
    ]
    if order_headers != expected_order_cols:
        errors.append(
            f"Orders columns mismatch. Expected {expected_order_cols}, got {order_headers}"
        )

    order_ids = set()
    for row in orders_rows:
        oid = row["order_id"]
        if oid in order_ids:
            errors.append(f"Duplicate order_id found: {oid}")
        order_ids.add(oid)
        try:
            amt = float(row["amount"])
            if amt <= 0:
                errors.append(f"Non-positive order amount: {oid}")
        except ValueError:
            errors.append(f"Invalid float amount for order: {oid}")

    # 4. Validate Payments CSV & Foreign Keys
    payment_headers, payments_rows = parse_csv_rows(gen_dir / "payments.csv")
    expected_payment_cols = [
        "payment_id",
        "order_id",
        "amount",
        "method",
        "utr",
        "created_at",
        "status",
    ]
    if payment_headers != expected_payment_cols:
        errors.append(
            f"Payments columns mismatch. Expected {expected_payment_cols}, got {payment_headers}"
        )

    payment_ids = set()
    for row in payments_rows:
        pid = row["payment_id"]
        if pid in payment_ids:
            errors.append(f"Duplicate payment_id found: {pid}")
        payment_ids.add(pid)
        # Foreign Key check
        if row["order_id"] not in order_ids:
            errors.append(
                f"Foreign key violation: Payment {pid} references unknown order {row['order_id']}"
            )

    # 5. Validate Invoices CSV & Foreign Keys
    inv_headers, invoices_rows = parse_csv_rows(gen_dir / "invoices.csv")
    expected_inv_cols = [
        "invoice_id",
        "order_id",
        "amount",
        "tax_lines_json",
        "created_at",
    ]
    if inv_headers != expected_inv_cols:
        errors.append(
            f"Invoices columns mismatch. Expected {expected_inv_cols}, got {inv_headers}"
        )

    inv_ids = set()
    for row in invoices_rows:
        iid = row["invoice_id"]
        if iid in inv_ids:
            errors.append(f"Duplicate invoice_id found: {iid}")
        inv_ids.add(iid)
        if row["order_id"] not in order_ids:
            errors.append(
                f"Foreign key violation: Invoice {iid} references unknown order {row['order_id']}"
            )
        try:
            json.loads(row["tax_lines_json"])
        except Exception:
            errors.append(f"Invalid tax_lines_json for invoice: {iid}")

    # 6. Validate Adjustments CSV
    adj_headers, adj_rows = parse_csv_rows(gen_dir / "adjustments.csv")
    expected_adj_cols = [
        "adjustment_id",
        "related_id",
        "type",
        "amount",
        "reason",
        "created_at",
    ]
    if adj_headers != expected_adj_cols:
        errors.append(
            f"Adjustments columns mismatch. Expected {expected_adj_cols}, got {adj_headers}"
        )

    adj_ids = set()
    for row in adj_rows:
        aid = row["adjustment_id"]
        if aid in adj_ids:
            errors.append(f"Duplicate adjustment_id found: {aid}")
        adj_ids.add(aid)

    # 7. Validate Settlements CSV
    settle_headers, settle_rows = parse_csv_rows(gen_dir / "settlements.csv")
    expected_settle_cols = ["settlement_id", "utr", "amount", "fees", "settled_at"]
    if settle_headers != expected_settle_cols:
        errors.append(
            f"Settlements columns mismatch. Expected {expected_settle_cols}, got {settle_headers}"
        )

    settle_ids = set()
    settle_utrs = set()
    for row in settle_rows:
        sid = row["settlement_id"]
        if sid in settle_ids:
            errors.append(f"Duplicate settlement_id found: {sid}")
        settle_ids.add(sid)
        settle_utrs.add(row["utr"])

    # 8. Validate Ground Truth CSV
    gt_headers, gt_rows = parse_csv_rows(gt_dir / "ground_truth.csv")
    expected_gt_cols = [
        "ground_truth_id",
        "order_id",
        "expected_scenario",
        "expected_outcome",
        "expected_resolution_class",
        "expected_root_cause",
        "expected_human_escalation",
        "expected_ai_investigation",
        "expected_confidence_band",
        "expected_financial_impact",
        "notes",
    ]
    if gt_headers != expected_gt_cols:
        errors.append(
            f"Ground truth columns mismatch. Expected {expected_gt_cols}, got {gt_headers}"
        )

    gt_ids = set()
    gt_order_ids = set()
    scenario_counts: dict[str, int] = {}
    resolution_counts: dict[str, int] = {}
    ai_resolvable_count = 0
    ai_escalation_count = 0

    for idx, row in enumerate(gt_rows, start=1):
        gid = row["ground_truth_id"]
        # Format check: GT-000001
        expected_gid = f"GT-{idx:06d}"
        if gid != expected_gid:
            errors.append(f"GT ID format error: expected {expected_gid}, got {gid}")
        if gid in gt_ids:
            errors.append(f"Duplicate ground_truth_id: {gid}")
        gt_ids.add(gid)

        oid = row["order_id"]
        if oid not in order_ids:
            errors.append(
                f"Ground truth references non-existent order_id: {oid} in {gid}"
            )
        gt_order_ids.add(oid)

        scen = row["expected_scenario"]
        scenario_counts[scen] = scenario_counts.get(scen, 0) + 1

        res_class = row["expected_resolution_class"]
        resolution_counts[res_class] = resolution_counts.get(res_class, 0) + 1

        is_human = row["expected_human_escalation"] == "True"
        is_ai = row["expected_ai_investigation"] == "True"

        if res_class == ResolutionClass.AI_INVESTIGATION.value:
            if not is_ai:
                errors.append(
                    f"Case {gid} is AI_INVESTIGATION but expected_ai_investigation is False"
                )
            if is_human:
                ai_escalation_count += 1
            else:
                ai_resolvable_count += 1

    # 9. Verify Target Distribution
    total_gt = len(gt_rows)
    if total_gt != DEFAULT_TOTAL_CASES:
        errors.append(
            f"Total cases count mismatch: expected {DEFAULT_TOTAL_CASES}, got {total_gt}"
        )

    det_res_count = resolution_counts.get(ResolutionClass.AUTO_RESOLVED.value, 0)
    det_esc_count = resolution_counts.get(
        ResolutionClass.DETERMINISTIC_ESCALATION.value, 0
    )
    ai_inv_count = resolution_counts.get(ResolutionClass.AI_INVESTIGATION.value, 0)

    # 780 (78.0%), 120 (12.0%), 100 (10.0%)
    if det_res_count != 780:
        errors.append(
            f"Deterministic resolution count mismatch: expected 780 (78%), got {det_res_count}"
        )
    if det_esc_count != 120:
        errors.append(
            f"Deterministic escalation count mismatch: expected 120 (12%), got {det_esc_count}"
        )
    if ai_inv_count != 100:
        errors.append(
            f"AI investigation count mismatch: expected 100 (10%), got {ai_inv_count}"
        )

    # 10. Verify AI Split: 50 AI-resolvable and 50 AI-escalation
    if ai_resolvable_count != 50:
        errors.append(
            f"AI-resolvable count mismatch: expected 50, got {ai_resolvable_count}"
        )
    if ai_escalation_count != 50:
        errors.append(
            f"AI-escalation count mismatch: expected 50, got {ai_escalation_count}"
        )

    # 11. Verify Multi-Order Settlement Batches
    multi_order_cases = scenario_counts.get(
        ScenarioType.MULTI_ORDER_SETTLEMENT.value, 0
    )
    if multi_order_cases != 60:
        errors.append(
            f"Multi-order settlement case count mismatch: expected 60, got {multi_order_cases}"
        )

    # Verify at least one batch UTR covers >= 2 payments
    batch_utr_counts: dict[str, int] = {}
    for p in payments_rows:
        if p["utr"] and "BATCH" in p["utr"]:
            batch_utr_counts[p["utr"]] = batch_utr_counts.get(p["utr"], 0) + 1

    if not any(count >= 2 for count in batch_utr_counts.values()):
        errors.append(
            "No multi-order settlement batch UTR with >= 2 payments was found"
        )

    # 12. Verify All 12 Scenarios Are Present
    for scen in ScenarioType:
        if scen.value not in scenario_counts or scenario_counts[scen.value] == 0:
            errors.append(f"Scenario {scen.value} has 0 cases in ground truth")

    # 13. Verify Timestamps derive from Anchor Date (no dates before anchor)
    anchor_iso = DEFAULT_ANCHOR_DATETIME.isoformat()
    for row in orders_rows:
        if row["created_at"] < anchor_iso:
            errors.append(
                f"Order {row['order_id']} created_at {row['created_at']} is before anchor {anchor_iso}"
            )

    is_valid = len(errors) == 0
    return is_valid, errors


# ============================================================================
# CLI ENTRYPOINT
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="ReconGuard Synthetic Data & Ground Truth Generator"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing generated dataset and ground truth files",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Deterministic random seed (default: {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--cases",
        type=int,
        default=DEFAULT_TOTAL_CASES,
        help=f"Total cases to generate (default: {DEFAULT_TOTAL_CASES})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom base data output directory",
    )

    args = parser.parse_args()

    base_dir = Path(args.output_dir) if args.output_dir else None

    if args.validate:
        print("[ReconGuard] Running dataset validation...")
        is_valid, errors = validate_dataset(base_dir)
        if is_valid:
            print("[ReconGuard] [OK] Validation SUCCESSFUL! All checks passed.")
            sys.exit(0)
        else:
            print(
                f"[ReconGuard] [FAIL] Validation FAILED with {len(errors)} error(s):"
            )
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)

    print(
        f"[ReconGuard] Generating {args.cases} synthetic reconciliation cases with SEED={args.seed}..."
    )
    generator = ReconciliationDataGenerator(
        seed=args.seed,
        total_cases=args.cases,
        anchor_datetime=DEFAULT_ANCHOR_DATETIME,
    )
    generator.generate_all()
    saved_files = generator.save_to_disk(base_dir)

    summary = generator.get_summary()
    print("\n" + "=" * 60)
    print("RECONGUARD DATASET GENERATION REPORT")
    print("=" * 60)
    print(f"Dataset Version:  {summary['dataset_version']}")
    print(f"Random Seed:      {summary['seed']}")
    print(f"Anchor Datetime:  {summary['anchor_datetime']}")
    print(f"Total Cases:      {summary['total_cases']}")
    print("\nResolution Distribution:")
    for key, val in summary["distribution"].items():
        if key == "ai_investigation":
            print(
                f"  - {key:<26}: {val['count']:>4} cases ({val['percentage']:>5.1f}%) [Target: {val['target_percentage']} %]"
            )
            print(
                f"      * AI-Resolvable         : {val['ai_resolvable']['count']:>4} cases ({val['ai_resolvable']['percentage']:>5.1f}%)"
            )
            print(
                f"      * AI-Escalation         : {val['ai_escalation']['count']:>4} cases ({val['ai_escalation']['percentage']:>5.1f}%)"
            )
        else:
            print(
                f"  - {key:<26}: {val['count']:>4} cases ({val['percentage']:>5.1f}%) [Target: {val['target_percentage']} %]"
            )

    print("\nScenario Breakdown (12 Scenarios):")
    for scen, count in summary["scenario_counts"].items():
        print(f"  - {scen:<30}: {count:>4} cases")

    print("\nGenerated Files:")
    for label, filepath in saved_files.items():
        print(f"  - {label:<20}: {filepath}")

    print("=" * 60)
    print("[ReconGuard] Generation completed successfully.")


if __name__ == "__main__":
    main()
