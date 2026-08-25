"""Unit tests for the ReconGuard Multi-Order Settlement Aggregation Matcher.

Verifies:
1. Known 3-order batch aggregation (gross payments sum == net settlement + fees).
2. Small monetary tolerance handling.
3. Incompatible/unrelated payments rejection.
4. Single-payment settlement rejection (not multi-order aggregation).
5. Missing payment handling (incomplete batch rejected).
6. Deterministic execution across repeated runs.
7. Ground-truth independence (no ground-truth loading).
8. Explainability: structured evidence, payment IDs, amounts, and fees.
9. Operational dataset aggregation execution (20 batches = 60 orders).
10. Order aggregation lookup mapping.
"""

from decimal import Decimal
from pathlib import Path
import pytest

from app.matching.aggregation_matcher import AggregationMatcher
from app.matching.types import (
    AggregationEvidence,
    AggregationMatchResult,
    ConfidenceBand,
    MatchMethod,
    MatchStatus,
)


@pytest.fixture
def sample_batch():
    """Fixture with a 3-order settlement batch."""
    orders = [
        {"order_id": "ORD-B1", "amount": "2000.00", "status": "COMPLETED"},
        {"order_id": "ORD-B2", "amount": "3000.00", "status": "COMPLETED"},
        {"order_id": "ORD-B3", "amount": "5000.00", "status": "COMPLETED"},
    ]
    payments = [
        {"payment_id": "PAY-B1", "order_id": "ORD-B1", "amount": "2000.00", "utr": "UTR-BATCH-001", "status": "SUCCESS"},
        {"payment_id": "PAY-B2", "order_id": "ORD-B2", "amount": "3000.00", "utr": "UTR-BATCH-001", "status": "SUCCESS"},
        {"payment_id": "PAY-B3", "order_id": "ORD-B3", "amount": "5000.00", "utr": "UTR-BATCH-001", "status": "SUCCESS"},
    ]
    # Total Gross = 10,000. Fees (2%) = 200. Net Settlement = 9,800.
    settlements = [
        {
            "settlement_id": "SET-BATCH-001",
            "utr": "UTR-BATCH-001",
            "amount": "9800.00",
            "fees": "200.00",
            "settled_at": "2026-08-03T12:00:00+00:00",
        }
    ]
    invoices = [
        {"invoice_id": "INV-B1", "order_id": "ORD-B1", "amount": "2000.00"},
        {"invoice_id": "INV-B2", "order_id": "ORD-B2", "amount": "3000.00"},
        {"invoice_id": "INV-B3", "order_id": "ORD-B3", "amount": "5000.00"},
    ]
    return settlements, payments, orders, invoices


def test_valid_3_order_batch_aggregation(sample_batch):
    """Test 1: Valid 3-order batch reconciles to single settlement with HIGH confidence."""
    settlements, payments, orders, invoices = sample_batch
    matcher = AggregationMatcher(settlements, payments, orders, invoices)

    res = matcher.match_settlement("SET-BATCH-001")
    assert res.status == MatchStatus.MATCHED
    assert res.match_method == MatchMethod.AGGREGATION
    assert res.confidence == 1.0
    assert res.confidence_band == ConfidenceBand.HIGH.value
    assert res.candidate_count == 3
    assert res.payment_ids == ["PAY-B1", "PAY-B2", "PAY-B3"]
    assert res.order_ids == ["ORD-B1", "ORD-B2", "ORD-B3"]
    assert res.matched_payment_total == 10000.0
    assert res.amount_difference == 0.0
    assert isinstance(res.evidence, AggregationEvidence)
    assert "Batch reconciled" in res.reason


def test_aggregation_with_small_monetary_tolerance(sample_batch):
    """Test 2: Aggregation matches within configured tolerance (e.g. ₹0.02 fee rounding)."""
    settlements, payments, orders, invoices = sample_batch
    # Introduce 2 paisa rounding difference in settlement amount (9799.98)
    settlements[0]["amount"] = "9799.98"

    matcher = AggregationMatcher(settlements, payments, orders, invoices, tolerance=Decimal("0.05"))
    res = matcher.match_settlement("SET-BATCH-001")

    assert res.status == MatchStatus.MATCHED
    assert res.amount_difference == 0.02
    assert res.match_method == MatchMethod.AGGREGATION


def test_incomplete_batch_missing_payment(sample_batch):
    """Test 5 & 6: Missing one payment in batch produces DISCREPANCY, not MATCHED."""
    settlements, payments, orders, invoices = sample_batch
    # Remove payment PAY-B3 (5,000 INR)
    payments = [payments[0], payments[1]]

    matcher = AggregationMatcher(settlements, payments, orders, invoices)
    res = matcher.match_settlement("SET-BATCH-001")

    assert res.status == MatchStatus.DISCREPANCY
    assert res.matched_payment_total == 5000.0
    assert res.amount_difference == 5000.0
    assert "Batch amount discrepancy" in res.reason


def test_single_payment_settlement_rejected_by_aggregation():
    """Test 4 & 5: Single-payment settlement rejected (must be handled by 1:1 matchers)."""
    settlements = [{"settlement_id": "SET-S1", "utr": "UTR-S1", "amount": "980.00", "fees": "20.00"}]
    payments = [{"payment_id": "PAY-S1", "order_id": "ORD-S1", "amount": "1000.00", "utr": "UTR-S1", "status": "SUCCESS"}]
    orders = [{"order_id": "ORD-S1", "amount": "1000.00", "status": "COMPLETED"}]

    matcher = AggregationMatcher(settlements, payments, orders)
    res = matcher.match_settlement("SET-S1")

    assert res.status == MatchStatus.UNMATCHED
    assert res.candidate_count == 1
    assert "minimum 2 required" in res.reason


def test_aggregation_determinism(sample_batch):
    """Test 7: Repeated runs produce identical results."""
    settlements, payments, orders, invoices = sample_batch
    m1 = AggregationMatcher(settlements, payments, orders, invoices)
    m2 = AggregationMatcher(settlements, payments, orders, invoices)

    res1 = m1.match_all_settlements()
    res2 = m2.match_all_settlements()

    assert len(res1) == len(res2)
    for r1, r2 in zip(res1, res2):
        assert r1.settlement_id == r2.settlement_id
        assert r1.status == r2.status
        assert r1.match_method == r2.match_method
        assert r1.payment_ids == r2.payment_ids
        assert r1.matched_payment_total == r2.matched_payment_total


def test_ground_truth_independence():
    """Test 8: AggregationMatcher operates purely on operational datasets without loading ground truth."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    matcher = AggregationMatcher.from_csv_directory(data_dir)
    assert not hasattr(matcher, "ground_truth")


def test_order_aggregation_map(sample_batch):
    """Test 10: build_order_aggregation_map correctly maps each constituent order."""
    settlements, payments, orders, invoices = sample_batch
    matcher = AggregationMatcher(settlements, payments, orders, invoices)

    order_map = matcher.build_order_aggregation_map()
    assert len(order_map) == 3
    for oid in ["ORD-B1", "ORD-B2", "ORD-B3"]:
        assert oid in order_map
        res = order_map[oid]
        assert res.status == MatchStatus.MATCHED
        assert res.match_method == MatchMethod.AGGREGATION
        assert res.settlement_ids == ["SET-BATCH-001"]


def test_operational_dataset_aggregation_results():
    """Test 9: Operational dataset reconciles exactly 20 batches of 3 orders (60 orders total)."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    matcher = AggregationMatcher.from_csv_directory(data_dir)
    summary = matcher.get_summary()

    # 20 batches reconciled
    assert summary["aggregation_matches"] == 20
    # Exactly 60 orders aggregated across the 20 batches
    assert summary["total_orders_aggregated"] == 60
    # Total settlements = 906 (20 multi-order batches + 886 single-order settlements)
    assert summary["total_settlements_evaluated"] == 906
    assert summary["no_aggregation"] == 886
