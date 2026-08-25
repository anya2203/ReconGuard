"""Unit tests for the ReconGuard Master Reconciliation Engine.

Verifies:
1. Clean exact match case -> EXACT / MATCHED.
2. Rounding discrepancy case -> FUZZY / MATCHED.
3. Reference typo case -> FUZZY / MATCHED.
4. Multi-order settlement batch -> AGGREGATION / MATCHED.
5. Multiple candidate payments (retry attempt) -> AMBIGUOUS.
6. Missing payment -> UNMATCHED.
7. Large amount discrepancy -> DISCREPANCY.
8. Active adjustments (chargeback / refund) -> DISCREPANCY.
9. Determinism across repeated executions.
10. Ground-truth independence (no ground-truth loading).
11. Cardinality check: every processed order receives exactly one final result.
12. Operational dataset baseline evaluation (1,000 cases).
"""

from pathlib import Path
import pytest

from app.matching.engine import ReconciliationEngine
from app.matching.types import (
    ConfidenceBand,
    MatchMethod,
    MatchResult,
    MatchStatus,
)


@pytest.fixture
def engine():
    """Load master reconciliation engine against operational dataset."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    return ReconciliationEngine.from_csv_directory(data_dir)


def test_clean_exact_case_matched(engine: ReconciliationEngine):
    """Test 1: Clean 1:1 transaction returns EXACT / MATCHED."""
    # ORD-000001 is a known clean exact match
    res = engine.reconcile_order("ORD-000001")
    assert res.status == MatchStatus.MATCHED
    assert res.match_method == MatchMethod.EXACT
    assert res.confidence == 1.0
    assert res.confidence_band == ConfidenceBand.HIGH.value
    assert len(res.payment_ids) == 1
    assert len(res.settlement_ids) == 1


def test_rounding_case_fuzzy_matched(engine: ReconciliationEngine):
    """Test 2: Rounding variance (< ₹1.00) returns FUZZY / MATCHED."""
    # ORD-000901 is a known rounding mismatch case
    res = engine.reconcile_order("ORD-000901")
    assert res.status == MatchStatus.MATCHED
    assert res.match_method == MatchMethod.FUZZY
    assert res.confidence_band == ConfidenceBand.HIGH.value
    assert res.financial_impact == 0.05


def test_reference_typo_fuzzy_matched(engine: ReconciliationEngine):
    """Test 3: UTR typo (transposed chars) returns FUZZY / MATCHED."""
    # ORD-000921 is a known reference typo case
    res = engine.reconcile_order("ORD-000921")
    assert res.status == MatchStatus.MATCHED
    assert res.match_method == MatchMethod.FUZZY
    assert res.confidence_band == ConfidenceBand.HIGH.value
    assert len(res.settlement_ids) == 1


def test_multi_order_batch_aggregation_matched(engine: ReconciliationEngine):
    """Test 4: Multi-order batch orders return AGGREGATION / MATCHED."""
    # ORD-000721 to ORD-000723 are batch 1 orders
    for oid in ["ORD-000721", "ORD-000722", "ORD-000723"]:
        res = engine.reconcile_order(oid)
        assert res.status == MatchStatus.MATCHED
        assert res.match_method == MatchMethod.AGGREGATION
        assert res.confidence == 1.0
        assert res.settlement_ids == ["SET-BATCH-0001"]


def test_multiple_candidate_payments_ambiguous(engine: ReconciliationEngine):
    """Test 5: Multiple payment retry candidates return AMBIGUOUS."""
    # ORD-000951 is a known ambiguous candidate retry case
    res = engine.reconcile_order("ORD-000951")
    assert res.status == MatchStatus.AMBIGUOUS
    assert res.match_method == MatchMethod.NONE
    assert len(res.payment_ids) == 2


def test_missing_payment_unmatched(engine: ReconciliationEngine):
    """Test 7: Missing payment returns UNMATCHED."""
    # ORD-000829 is a known missing payment case
    res = engine.reconcile_order("ORD-000829")
    assert res.status == MatchStatus.UNMATCHED
    assert res.match_method == MatchMethod.NONE
    assert len(res.payment_ids) == 0


def test_amount_mismatch_discrepancy(engine: ReconciliationEngine):
    """Test 8: Significant amount mismatch returns DISCREPANCY."""
    # ORD-000781 is a known amount mismatch case
    res = engine.reconcile_order("ORD-000781")
    assert res.status == MatchStatus.DISCREPANCY
    assert res.match_method == MatchMethod.NONE


def test_refund_and_chargeback_discrepancy(engine: ReconciliationEngine):
    """Test 9: Transactions with chargeback or refund return DISCREPANCY."""
    # Chargeback case (ORD-000853)
    res_cb = engine.reconcile_order("ORD-000853")
    assert res_cb.status == MatchStatus.DISCREPANCY
    assert len(res_cb.adjustment_ids) > 0

    # Refund case (ORD-000877)
    res_rf = engine.reconcile_order("ORD-000877")
    assert res_rf.status == MatchStatus.DISCREPANCY
    assert len(res_rf.adjustment_ids) > 0


def test_engine_determinism(engine: ReconciliationEngine):
    """Test 10: Repeated engine executions produce identical results."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    engine2 = ReconciliationEngine.from_csv_directory(data_dir)

    res1 = engine.reconcile_all()
    res2 = engine2.reconcile_all()

    assert len(res1) == len(res2)
    for r1, r2 in zip(res1, res2):
        assert r1.order_id == r2.order_id
        assert r1.status == r2.status
        assert r1.match_method == r2.match_method
        assert r1.confidence == r2.confidence
        assert r1.payment_ids == r2.payment_ids
        assert r1.settlement_ids == r2.settlement_ids


def test_ground_truth_independence(engine: ReconciliationEngine):
    """Test 11: Master engine operates without loading ground truth."""
    assert not hasattr(engine, "ground_truth")


def test_every_order_receives_exact_one_result(engine: ReconciliationEngine):
    """Test 12: Every order in orders.csv receives exactly 1 distinct MatchResult."""
    results = engine.reconcile_all()
    assert len(results) == 1000
    seen_orders = set()
    for r in results:
        assert r.order_id not in seen_orders
        seen_orders.add(r.order_id)
        assert isinstance(r.status, MatchStatus)
        assert isinstance(r.match_method, MatchMethod)


def test_full_dataset_reconciliation_statistics(engine: ReconciliationEngine):
    """Test 13: Full operational dataset produces 820 MATCHED cases (720 exact + 40 fuzzy + 60 aggregation)."""
    summary = engine.get_summary()

    assert summary["total_processed"] == 1000

    # MATCHED Total = 820 (82.0%)
    assert summary["matched"] == 820
    assert summary["matched_percentage"] == 82.0

    # Method Breakdown
    breakdown = summary["matched_breakdown"]
    assert breakdown["EXACT"] == 720
    assert breakdown["EXACT_percentage"] == 72.0
    assert breakdown["FUZZY"] == 40
    assert breakdown["FUZZY_percentage"] == 4.0
    assert breakdown["AGGREGATION"] == 60
    assert breakdown["AGGREGATION_percentage"] == 6.0

    # Non-Matched Categories (180 cases total)
    assert summary["ambiguous"] in [20, 21]
    assert summary["unmatched"] == 44
    assert summary["unmatched_percentage"] == 4.4
    assert summary["discrepancy"] in [115, 116]

    # Invariant: Matched + Ambiguous + Unmatched + Discrepancy == Total
    assert summary["matched"] + summary["ambiguous"] + summary["unmatched"] + summary["discrepancy"] == 1000

