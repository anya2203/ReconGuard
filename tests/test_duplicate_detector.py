"""Unit tests for the ReconGuard Deterministic Duplicate Detector.

Verifies:
1. True duplicate detection (same UTR, same amount, repeated capture).
2. Same order, distinct payments not falsely classified as exact duplicate.
3. Same amount on distinct independent transactions (no false duplicate).
4. Same UTR across payments triggers DUPLICATE classification.
5. Distinct UTRs on multi-payment orders classified as AMBIGUOUS (retry attempt).
6. Timestamp window scoring behavior.
7. Ambiguous multi-candidate handling (does not force DUPLICATE).
8. Single payment case returns NO_DUPLICATE.
9. Determinism across repeated executions.
10. Ground-truth independence (no ground-truth loading).
11. Operational dataset duplicate evaluation statistics.
12. Non-interference with exact and fuzzy matching results.
"""

from pathlib import Path
import pytest

from app.matching.duplicate_detector import DuplicateDetector
from app.matching.exact_matcher import ExactMatcher
from app.matching.fuzzy_matcher import FuzzyMatcher
from app.matching.types import (
    DuplicateClassification,
    DuplicateDetectionResult,
    DuplicateEvidence,
    MatchStatus,
)


def test_true_duplicate_same_utr_and_amount():
    """Test 1 & 4: Payments with identical UTR and amount classified as DUPLICATE."""
    payments = [
        {
            "payment_id": "PAY-DUP-001A",
            "order_id": "ORD-DUP-001",
            "amount": "2500.00",
            "method": "UPI",
            "utr": "UTR-DUP-12345",
            "created_at": "2026-08-01T10:00:00+00:00",
            "status": "SUCCESS",
        },
        {
            "payment_id": "PAY-DUP-001B",
            "order_id": "ORD-DUP-001",
            "amount": "2500.00",
            "method": "UPI",
            "utr": "UTR-DUP-12345",  # Identical UTR
            "created_at": "2026-08-01T10:00:15+00:00",  # 15s later
            "status": "SUCCESS",
        },
    ]
    orders = [{"order_id": "ORD-DUP-001", "amount": "2500.00", "status": "COMPLETED"}]

    detector = DuplicateDetector(payments, orders)
    res = detector.detect_duplicates_for_order("ORD-DUP-001")

    assert res.classification == DuplicateClassification.DUPLICATE
    assert res.confidence >= 0.90
    assert len(res.candidate_pairs) == 1
    assert res.candidate_pairs[0].same_utr is True
    assert res.candidate_pairs[0].same_amount is True
    assert "Confirmed duplicate payment" in res.reason


def test_retry_attempt_different_utr_is_ambiguous():
    """Test 2, 5 & 7: Same order, same amount, but distinct UTRs classified as AMBIGUOUS."""
    payments = [
        {
            "payment_id": "PAY-RETRY-001",
            "order_id": "ORD-RETRY-001",
            "amount": "2499.00",
            "method": "UPI",
            "utr": "UTR-IND-000100A",
            "created_at": "2026-08-01T10:02:00+00:00",
            "status": "SUCCESS",
        },
        {
            "payment_id": "PAY-RETRY-002",
            "order_id": "ORD-RETRY-001",
            "amount": "2499.00",
            "method": "UPI",
            "utr": "UTR-IND-000100B",  # Distinct UTR
            "created_at": "2026-08-01T10:04:00+00:00",  # 2 min retry
            "status": "SUCCESS",
        },
    ]
    orders = [{"order_id": "ORD-RETRY-001", "amount": "2499.00", "status": "COMPLETED"}]

    detector = DuplicateDetector(payments, orders)
    res = detector.detect_duplicates_for_order("ORD-RETRY-001")

    # MUST NOT be DUPLICATE; it is AMBIGUOUS retry candidate
    assert res.classification == DuplicateClassification.AMBIGUOUS
    assert res.classification != DuplicateClassification.DUPLICATE
    assert res.candidate_pairs[0].same_utr is False
    assert "customer retry" in res.reason.lower() or "ambiguous" in res.reason.lower()


def test_same_amount_distinct_orders_no_duplicate():
    """Test 3: Different orders with identical amount are independent (NO_DUPLICATE)."""
    p1 = {
        "payment_id": "PAY-001",
        "order_id": "ORD-001",
        "amount": "999.00",
        "method": "UPI",
        "utr": "UTR-001",
        "created_at": "2026-08-01T10:00:00+00:00",
    }
    p2 = {
        "payment_id": "PAY-002",
        "order_id": "ORD-002",
        "amount": "999.00",
        "method": "UPI",
        "utr": "UTR-002",
        "created_at": "2026-08-01T10:00:00+00:00",
    }

    detector = DuplicateDetector([p1, p2])
    pair_ev = detector.evaluate_pair(p1, p2)

    assert pair_ev.classification == DuplicateClassification.NO_DUPLICATE.value
    assert pair_ev.same_order is False
    assert pair_ev.same_utr is False


def test_timestamp_window_scoring():
    """Test 6: Tight timestamps score higher than distant timestamps."""
    p_base = {
        "payment_id": "P1",
        "order_id": "O1",
        "amount": "1000.00",
        "method": "UPI",
        "utr": "UTR-X",
        "created_at": "2026-08-01T10:00:00+00:00",
    }
    p_tight = {
        "payment_id": "P2",
        "order_id": "O1",
        "amount": "1000.00",
        "method": "UPI",
        "utr": "UTR-X",
        "created_at": "2026-08-01T10:00:30+00:00",  # 30s diff
    }
    p_distant = {
        "payment_id": "P3",
        "order_id": "O1",
        "amount": "1000.00",
        "method": "UPI",
        "utr": "UTR-X",
        "created_at": "2026-08-03T10:00:00+00:00",  # 2 days diff
    }

    detector = DuplicateDetector([p_base, p_tight, p_distant])
    ev_tight = detector.evaluate_pair(p_base, p_tight)
    ev_distant = detector.evaluate_pair(p_base, p_distant)

    assert ev_tight.timestamp_difference_seconds == 30.0
    assert ev_tight.duplicate_score > ev_distant.duplicate_score


def test_single_payment_no_duplicate():
    """Test 8: Order with single payment returns NO_DUPLICATE."""
    payments = [
        {
            "payment_id": "PAY-SINGLE-001",
            "order_id": "ORD-SINGLE-001",
            "amount": "500.00",
            "method": "UPI",
            "utr": "UTR-SINGLE-001",
            "created_at": "2026-08-01T10:00:00+00:00",
            "status": "SUCCESS",
        }
    ]
    orders = [{"order_id": "ORD-SINGLE-001", "amount": "500.00", "status": "COMPLETED"}]

    detector = DuplicateDetector(payments, orders)
    res = detector.detect_duplicates_for_order("ORD-SINGLE-001")

    assert res.classification == DuplicateClassification.NO_DUPLICATE
    assert len(res.duplicate_payment_ids) == 0
    assert res.primary_payment_id == "PAY-SINGLE-001"


def test_duplicate_detector_determinism():
    """Test 9: Repeated runs produce identical results."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    det1 = DuplicateDetector.from_csv_directory(data_dir)
    res1 = det1.detect_all()

    det2 = DuplicateDetector.from_csv_directory(data_dir)
    res2 = det2.detect_all()

    assert len(res1) == len(res2)
    for r1, r2 in zip(res1, res2):
        assert r1.order_id == r2.order_id
        assert r1.classification == r2.classification
        assert r1.primary_payment_id == r2.primary_payment_id
        assert r1.duplicate_payment_ids == r2.duplicate_payment_ids
        assert r1.reason == r2.reason


def test_ground_truth_independence():
    """Test 10: DuplicateDetector operates purely on operational datasets without loading ground truth."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    detector = DuplicateDetector.from_csv_directory(data_dir)
    assert not hasattr(detector, "ground_truth")


def test_operational_dataset_detection_summary():
    """Test 11: Operational dataset identifies exactly 20 ambiguous retry groups and 0 false duplicates."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    detector = DuplicateDetector.from_csv_directory(data_dir)
    summary = detector.get_summary()

    assert summary["total_orders_evaluated"] == 1000
    assert summary["total_payments_indexed"] == 976  # 976 payments across 1000 orders
    assert summary["candidate_pairs_examined"] == 20  # 20 orders have 2 payments
    # The 20 multi-payment cases are retry attempts (distinct UTRs) -> AMBIGUOUS
    assert summary["ambiguous_candidate_groups"] == 20
    assert summary["duplicates_detected"] == 0
    assert summary["no_duplicate_cases"] == 980


def test_non_interference_with_exact_and_fuzzy_results():
    """Test 12: Existing exact and fuzzy matching results remain stable."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    exact_matcher = ExactMatcher.from_csv_directory(data_dir)
    fuzzy_matcher = FuzzyMatcher.from_csv_directory(data_dir)

    exact_summary = exact_matcher.get_summary()
    assert exact_summary["matched"] == 720

    fuzzy_summary = fuzzy_matcher.get_summary()
    assert fuzzy_summary["matched_total"] == 760
    assert fuzzy_summary["matched_exact"] == 720
    assert fuzzy_summary["matched_fuzzy"] == 40

