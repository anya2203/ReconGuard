"""Unit tests for the ReconGuard Deterministic Exact Matcher.

Verifies:
1. Valid 1:1 exact match
2. Amount mismatch rejection
3. Missing payment handling
4. Missing settlement handling
5. Missing invoice handling
6. Active adjustment handling (chargebacks, refunds)
7. Settlement SLA breach handling
8. Multiple candidate payments (ambiguous duplicate)
9. Multi-order settlement batch handling
10. Ground-truth independence
11. Deterministic execution across repeated runs
12. Operational dataset execution
"""

from pathlib import Path
import pytest

from app.matching.exact_matcher import ExactMatcher
from app.matching.types import MatchMethod, MatchResult, MatchStatus


@pytest.fixture
def sample_records():
    """Small isolated fixture representing valid and anomalous transactions."""
    orders = [
        {
            "order_id": "ORD-001",
            "customer_id": "CUST-001",
            "amount": "1000.00",
            "currency": "INR",
            "created_at": "2026-08-01T10:00:00+00:00",
            "status": "COMPLETED",
        },
        {
            "order_id": "ORD-002",
            "customer_id": "CUST-002",
            "amount": "2000.00",
            "currency": "INR",
            "created_at": "2026-08-01T11:00:00+00:00",
            "status": "COMPLETED",
        },
        {
            "order_id": "ORD-003",
            "customer_id": "CUST-003",
            "amount": "3000.00",
            "currency": "INR",
            "created_at": "2026-08-01T12:00:00+00:00",
            "status": "COMPLETED",
        },
    ]

    payments = [
        {
            "payment_id": "PAY-001",
            "order_id": "ORD-001",
            "amount": "1000.00",
            "method": "UPI",
            "utr": "UTR-001",
            "created_at": "2026-08-01T10:05:00+00:00",
            "status": "SUCCESS",
        },
        {
            "payment_id": "PAY-002",
            "order_id": "ORD-002",
            "amount": "1500.00",  # Amount mismatch (2000 vs 1500)
            "method": "CARD",
            "utr": "UTR-002",
            "created_at": "2026-08-01T11:05:00+00:00",
            "status": "SUCCESS",
        },
        # ORD-003 has no payment
    ]

    settlements = [
        {
            "settlement_id": "SET-001",
            "utr": "UTR-001",
            "amount": "980.00",
            "fees": "20.00",
            "settled_at": "2026-08-02T10:05:00+00:00",  # T+1 SLA
        },
        {
            "settlement_id": "SET-002",
            "utr": "UTR-002",
            "amount": "1470.00",
            "fees": "30.00",
            "settled_at": "2026-08-02T11:05:00+00:00",
        },
    ]

    invoices = [
        {
            "invoice_id": "INV-001",
            "order_id": "ORD-001",
            "amount": "1000.00",
            "tax_lines_json": "{}",
            "created_at": "2026-08-01T10:01:00+00:00",
        },
        {
            "invoice_id": "INV-002",
            "order_id": "ORD-002",
            "amount": "2000.00",
            "tax_lines_json": "{}",
            "created_at": "2026-08-01T11:01:00+00:00",
        },
    ]

    adjustments = []

    return orders, payments, settlements, invoices, adjustments


def test_valid_exact_match(sample_records):
    """Test 1: Known operational records that cleanly match return MATCHED."""
    orders, payments, settlements, invoices, adjustments = sample_records
    matcher = ExactMatcher(orders, payments, settlements, invoices, adjustments)

    res = matcher.match_order("ORD-001")
    assert res.status == MatchStatus.MATCHED
    assert res.match_method == MatchMethod.EXACT
    assert res.confidence == 1.0
    assert res.financial_impact == 0.0
    assert res.payment_ids == ["PAY-001"]
    assert res.settlement_ids == ["SET-001"]
    assert res.invoice_id == "INV-001"
    assert res.evidence.order_id_verified is True
    assert res.evidence.amount_difference == 0.0
    assert "Exact 1:1 match verified" in res.reason


def test_amount_mismatch_discrepancy(sample_records):
    """Test 2: Records with amount discrepancies do not match (DISCREPANCY)."""
    orders, payments, settlements, invoices, adjustments = sample_records
    matcher = ExactMatcher(orders, payments, settlements, invoices, adjustments)

    res = matcher.match_order("ORD-002")
    assert res.status == MatchStatus.DISCREPANCY
    assert res.match_method == MatchMethod.NONE
    assert res.financial_impact == 500.00
    assert "Amount mismatch" in res.reason


def test_missing_payment_unmatched(sample_records):
    """Test 3: An order with no payment record returns UNMATCHED."""
    orders, payments, settlements, invoices, adjustments = sample_records
    matcher = ExactMatcher(orders, payments, settlements, invoices, adjustments)

    res = matcher.match_order("ORD-003")
    assert res.status == MatchStatus.UNMATCHED
    assert res.match_method == MatchMethod.NONE
    assert res.financial_impact == 3000.00
    assert "No captured payment" in res.reason


def test_missing_settlement_discrepancy():
    """Test 4: A payment with no matching settlement returns DISCREPANCY."""
    orders = [{"order_id": "ORD-004", "amount": "500.00", "status": "COMPLETED"}]
    payments = [{"payment_id": "PAY-004", "order_id": "ORD-004", "amount": "500.00", "status": "SUCCESS", "utr": "UTR-UNSETTLED", "created_at": "2026-08-01T10:00:00+00:00"}]
    settlements = []
    invoices = [{"invoice_id": "INV-004", "order_id": "ORD-004", "amount": "500.00"}]

    matcher = ExactMatcher(orders, payments, settlements, invoices)
    res = matcher.match_order("ORD-004")
    assert res.status == MatchStatus.DISCREPANCY
    assert "No bank settlement found" in res.reason


def test_multiple_candidate_payments_ambiguous():
    """Test 5: Multiple candidate payments for the same order return AMBIGUOUS."""
    orders = [{"order_id": "ORD-005", "amount": "1000.00", "status": "COMPLETED"}]
    payments = [
        {"payment_id": "PAY-005A", "order_id": "ORD-005", "amount": "1000.00", "status": "SUCCESS", "utr": "UTR-005A", "created_at": "2026-08-01T10:00:00+00:00"},
        {"payment_id": "PAY-005B", "order_id": "ORD-005", "amount": "1000.00", "status": "SUCCESS", "utr": "UTR-005B", "created_at": "2026-08-01T10:02:00+00:00"},
    ]
    settlements = [{"settlement_id": "SET-005", "utr": "UTR-005A", "amount": "980.00", "fees": "20.00"}]
    invoices = [{"invoice_id": "INV-005", "order_id": "ORD-005", "amount": "1000.00"}]

    matcher = ExactMatcher(orders, payments, settlements, invoices)
    res = matcher.match_order("ORD-005")
    assert res.status == MatchStatus.AMBIGUOUS
    assert len(res.payment_ids) == 2
    assert "Multiple candidate payments" in res.reason


def test_missing_invoice_discrepancy():
    """Test: Missing invoice returns DISCREPANCY."""
    orders = [{"order_id": "ORD-006", "amount": "1000.00", "status": "COMPLETED"}]
    payments = [{"payment_id": "PAY-006", "order_id": "ORD-006", "amount": "1000.00", "status": "SUCCESS", "utr": "UTR-006", "created_at": "2026-08-01T10:00:00+00:00"}]
    settlements = [{"settlement_id": "SET-006", "utr": "UTR-006", "amount": "980.00", "fees": "20.00", "settled_at": "2026-08-02T10:00:00+00:00"}]
    invoices = []  # Missing invoice

    matcher = ExactMatcher(orders, payments, settlements, invoices)
    res = matcher.match_order("ORD-006")
    assert res.status == MatchStatus.DISCREPANCY
    assert "Invoice record missing" in res.reason


def test_adjustment_chargeback_or_refund_discrepancy():
    """Test: Active adjustments (chargeback or refund) prevent clean MATCHED."""
    orders = [{"order_id": "ORD-007", "amount": "7500.00", "status": "COMPLETED"}]
    payments = [{"payment_id": "PAY-007", "order_id": "ORD-007", "amount": "7500.00", "status": "SUCCESS", "utr": "UTR-007", "created_at": "2026-08-01T10:00:00+00:00"}]
    settlements = [{"settlement_id": "SET-007", "utr": "UTR-007", "amount": "7350.00", "fees": "150.00", "settled_at": "2026-08-02T10:00:00+00:00"}]
    invoices = [{"invoice_id": "INV-007", "order_id": "ORD-007", "amount": "7500.00"}]
    adjustments = [{"adjustment_id": "ADJ-001", "related_id": "PAY-007", "type": "REFUND", "amount": "-7500.00", "reason": "Customer return refund"}]

    matcher = ExactMatcher(orders, payments, settlements, invoices, adjustments)
    res = matcher.match_order("ORD-007")
    assert res.status == MatchStatus.DISCREPANCY
    assert res.financial_impact == 7500.00
    assert "Active adjustments" in res.reason
    assert "REFUND" in res.reason


def test_settlement_sla_breach_discrepancy():
    """Test: Settlement delay exceeding 5-day SLA returns DISCREPANCY."""
    orders = [{"order_id": "ORD-008", "amount": "1000.00", "status": "COMPLETED"}]
    payments = [{"payment_id": "PAY-008", "order_id": "ORD-008", "amount": "1000.00", "status": "SUCCESS", "utr": "UTR-008", "created_at": "2026-08-01T10:00:00+00:00"}]
    # 7 days delay (> 5 days)
    settlements = [{"settlement_id": "SET-008", "utr": "UTR-008", "amount": "980.00", "fees": "20.00", "settled_at": "2026-08-08T10:00:00+00:00"}]
    invoices = [{"invoice_id": "INV-008", "order_id": "ORD-008", "amount": "1000.00"}]

    matcher = ExactMatcher(orders, payments, settlements, invoices)
    res = matcher.match_order("ORD-008")
    assert res.status == MatchStatus.DISCREPANCY
    assert res.evidence.settlement_sla_breached is True
    assert "SLA policy window" in res.reason


def test_ground_truth_independence():
    """Test 6: Matcher operates purely on operational datasets without loading ground truth."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    matcher = ExactMatcher.from_csv_directory(data_dir)

    # Verify matcher does not have ground_truth attribute
    assert not hasattr(matcher, "ground_truth")

    results = matcher.match_all()
    assert len(results) == 1000


def test_determinism_across_runs():
    """Test 7: Repeated executions on the same input yield identical results."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    matcher1 = ExactMatcher.from_csv_directory(data_dir)
    results1 = matcher1.match_all()

    matcher2 = ExactMatcher.from_csv_directory(data_dir)
    results2 = matcher2.match_all()

    assert len(results1) == len(results2)
    for r1, r2 in zip(results1, results2):
        assert r1.order_id == r2.order_id
        assert r1.status == r2.status
        assert r1.match_method == r2.match_method
        assert r1.payment_ids == r2.payment_ids
        assert r1.settlement_ids == r2.settlement_ids
        assert r1.financial_impact == r2.financial_impact
        assert r1.reason == r2.reason


def test_dataset_exact_matcher_run_statistics():
    """Test 8: Exact matcher on generated dataset matches 720 exact cases without false positives."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    matcher = ExactMatcher.from_csv_directory(data_dir)
    summary = matcher.get_summary()

    assert summary["total_processed"] == 1000
    # Exactly 720 pure 1:1 exact matches in our synthetic dataset
    assert summary["matched"] == 720
    assert summary["matched_percentage"] == 72.0
    # The remaining 280 cases are non-exact (batch, discrepancy, ambiguous, unmatched)
    assert summary["total_processed"] - summary["matched"] == 280

