"""Unit tests for the ReconGuard Deterministic Fuzzy Matcher.

Verifies:
1. Exact candidate with minor amount difference (rounding mismatch) produces HIGH confidence fuzzy match.
2. Rounding difference within configured tolerance matches cleanly.
3. Reference typo (transposed digits) identifies the correct candidate with high confidence.
4. Large amount difference (e.g. 30% mismatch) is rejected and flagged as DISCREPANCY.
5. Unrelated / distant date candidate is rejected.
6. Multiple plausible candidates return AMBIGUOUS.
7. Weak / uncorroborated candidate returns UNMATCHED.
8. Candidate scoring determinism across repeated executions.
9. Ground-truth independence (no ground-truth loading).
10. Explainability: structured evidence, component scores, and confidence bands.
11. Delayed settlement candidate identification with SLA breach flag.
12. Operational dataset execution without over-matching.
"""

from pathlib import Path
import pytest

from app.matching.fuzzy_matcher import FuzzyMatcher
from app.matching.types import (
    ConfidenceBand,
    FuzzyMatchEvidence,
    MatchMethod,
    MatchResult,
    MatchStatus,
)


@pytest.fixture
def base_order():
    return {
        "order_id": "ORD-FZ-001",
        "customer_id": "CUST-001",
        "amount": "1499.50",
        "currency": "INR",
        "created_at": "2026-08-01T12:00:00+00:00",
        "status": "COMPLETED",
    }


def test_minor_rounding_difference_fuzzy_match(base_order):
    """Test 1 & 2: Minor rounding difference (₹0.05) produces HIGH confidence FUZZY match."""
    orders = [base_order]
    # Payment has 5 paisa difference due to GST rounding
    payments = [
        {
            "payment_id": "PAY-FZ-001",
            "order_id": "ORD-FZ-001",
            "amount": "1499.55",
            "method": "UPI",
            "utr": "UTR-IND-99990001",
            "created_at": "2026-08-01T12:05:00+00:00",
            "status": "SUCCESS",
        }
    ]
    settlements = [
        {
            "settlement_id": "SET-FZ-001",
            "utr": "UTR-IND-99990001",
            "amount": "1469.56",
            "fees": "29.99",
            "settled_at": "2026-08-02T12:05:00+00:00",
        }
    ]
    invoices = [
        {
            "invoice_id": "INV-FZ-001",
            "order_id": "ORD-FZ-001",
            "amount": "1499.50",
        }
    ]

    matcher = FuzzyMatcher(orders, payments, settlements, invoices, amount_tolerance_abs=1.0)
    res = matcher.match_order("ORD-FZ-001")

    assert res.status == MatchStatus.MATCHED
    assert res.match_method == MatchMethod.FUZZY
    assert res.confidence_band == ConfidenceBand.HIGH.value
    assert res.confidence >= 0.90
    assert res.financial_impact == 0.05
    assert isinstance(res.evidence, FuzzyMatchEvidence)
    assert res.evidence.amount_difference == 0.05
    assert res.evidence.amount_score >= 0.95


def test_reference_typo_fuzzy_match(base_order):
    """Test 3: UTR with 2 transposed characters is recognized with HIGH confidence."""
    orders = [base_order]
    payments = [
        {
            "payment_id": "PAY-FZ-002",
            "order_id": "ORD-FZ-001",
            "amount": "1499.50",
            "method": "UPI",
            "utr": "UTR-IND-00085112",  # Payment UTR ending in 12
            "created_at": "2026-08-01T12:05:00+00:00",
            "status": "SUCCESS",
        }
    ]
    # Bank settlement has typo: ending in 21
    settlements = [
        {
            "settlement_id": "SET-FZ-002",
            "utr": "UTR-IND-00085121",  # Settlement UTR ending in 21
            "amount": "1469.51",
            "fees": "29.99",
            "settled_at": "2026-08-02T12:05:00+00:00",
        }
    ]
    invoices = [
        {
            "invoice_id": "INV-FZ-002",
            "order_id": "ORD-FZ-001",
            "amount": "1499.50",
        }
    ]

    matcher = FuzzyMatcher(orders, payments, settlements, invoices)
    res = matcher.match_order("ORD-FZ-001")

    assert res.status == MatchStatus.MATCHED
    assert res.match_method == MatchMethod.FUZZY
    assert res.confidence_band == ConfidenceBand.HIGH.value
    assert res.settlement_ids == ["SET-FZ-002"]
    assert res.evidence.reference_similarity >= 0.85
    assert "Fuzzy match verified with HIGH confidence" in res.reason


def test_large_amount_difference_rejected(base_order):
    """Test 4: Large amount discrepancy (30% difference) is rejected as DISCREPANCY."""
    orders = [base_order]  # 1499.50
    payments = [
        {
            "payment_id": "PAY-FZ-003",
            "order_id": "ORD-FZ-001",
            "amount": "999.00",  # ~33% discrepancy
            "method": "UPI",
            "utr": "UTR-IND-99990003",
            "created_at": "2026-08-01T12:05:00+00:00",
            "status": "SUCCESS",
        }
    ]
    settlements = [
        {
            "settlement_id": "SET-FZ-003",
            "utr": "UTR-IND-99990003",
            "amount": "979.02",
            "fees": "19.98",
            "settled_at": "2026-08-02T12:05:00+00:00",
        }
    ]
    invoices = [{"invoice_id": "INV-FZ-003", "order_id": "ORD-FZ-001", "amount": "1499.50"}]

    matcher = FuzzyMatcher(orders, payments, settlements, invoices)
    res = matcher.match_order("ORD-FZ-001")

    assert res.status == MatchStatus.DISCREPANCY
    assert res.match_method == MatchMethod.NONE
    assert res.confidence_band == ConfidenceBand.LOW.value
    assert res.financial_impact == 500.50
    assert "Large amount mismatch" in res.reason


def test_unrelated_date_candidate_rejected(base_order):
    """Test 5: Settlement settled 60 days later is rejected by date window."""
    orders = [base_order]
    payments = [
        {
            "payment_id": "PAY-FZ-004",
            "order_id": "ORD-FZ-001",
            "amount": "1499.50",
            "method": "UPI",
            "utr": "UTR-IND-99990004",
            "created_at": "2026-08-01T12:05:00+00:00",
            "status": "SUCCESS",
        }
    ]
    # 60 days later (> 14 days window)
    settlements = [
        {
            "settlement_id": "SET-FZ-004",
            "utr": "UTR-IND-99990004",
            "amount": "1469.51",
            "fees": "29.99",
            "settled_at": "2026-10-01T12:05:00+00:00",
        }
    ]
    invoices = [{"invoice_id": "INV-FZ-004", "order_id": "ORD-FZ-001", "amount": "1499.50"}]

    matcher = FuzzyMatcher(orders, payments, settlements, invoices, date_window_days=14.0)
    res = matcher.match_order("ORD-FZ-001")

    assert res.status == MatchStatus.DISCREPANCY
    assert res.status != MatchStatus.MATCHED
    assert res.confidence_band != ConfidenceBand.HIGH.value


def test_multiple_plausible_candidates_ambiguous(base_order):
    """Test 6: Multiple candidate payments for same order return AMBIGUOUS."""
    orders = [base_order]
    payments = [
        {
            "payment_id": "PAY-FZ-005A",
            "order_id": "ORD-FZ-001",
            "amount": "1499.50",
            "method": "UPI",
            "utr": "UTR-IND-005A",
            "created_at": "2026-08-01T12:02:00+00:00",
            "status": "SUCCESS",
        },
        {
            "payment_id": "PAY-FZ-005B",
            "order_id": "ORD-FZ-001",
            "amount": "1499.50",
            "method": "UPI",
            "utr": "UTR-IND-005B",
            "created_at": "2026-08-01T12:04:00+00:00",
            "status": "SUCCESS",
        },
    ]
    settlements = [
        {"settlement_id": "SET-FZ-005", "utr": "UTR-IND-005A", "amount": "1469.51", "fees": "29.99"}
    ]
    invoices = [{"invoice_id": "INV-FZ-005", "order_id": "ORD-FZ-001", "amount": "1499.50"}]

    matcher = FuzzyMatcher(orders, payments, settlements, invoices)
    res = matcher.match_order("ORD-FZ-001")

    assert res.status == MatchStatus.AMBIGUOUS
    assert len(res.payment_ids) == 2


def test_weak_candidate_unmatched(base_order):
    """Test 7: Order with no payments returns UNMATCHED."""
    orders = [base_order]
    payments = []
    settlements = []
    invoices = [{"invoice_id": "INV-FZ-007", "order_id": "ORD-FZ-001", "amount": "1499.50"}]

    matcher = FuzzyMatcher(orders, payments, settlements, invoices)
    res = matcher.match_order("ORD-FZ-001")

    assert res.status == MatchStatus.UNMATCHED
    assert res.confidence_band == ConfidenceBand.NONE.value


def test_candidate_scoring_determinism():
    """Test 8: Same operational dataset yields identical scores across runs."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    matcher1 = FuzzyMatcher.from_csv_directory(data_dir)
    res1 = matcher1.match_all()

    matcher2 = FuzzyMatcher.from_csv_directory(data_dir)
    res2 = matcher2.match_all()

    assert len(res1) == len(res2)
    for r1, r2 in zip(res1, res2):
        assert r1.order_id == r2.order_id
        assert r1.status == r2.status
        assert r1.match_method == r2.match_method
        assert r1.confidence == r2.confidence
        assert r1.confidence_band == r2.confidence_band
        assert r1.reason == r2.reason


def test_ground_truth_independence():
    """Test 9: Matcher operates purely on operational datasets without loading ground truth."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    matcher = FuzzyMatcher.from_csv_directory(data_dir)
    assert not hasattr(matcher, "ground_truth")


def test_explainable_evidence_structure(base_order):
    """Test 10: Result contains full structured scoring and evidence fields."""
    orders = [base_order]
    payments = [
        {
            "payment_id": "PAY-FZ-010",
            "order_id": "ORD-FZ-001",
            "amount": "1499.50",
            "method": "UPI",
            "utr": "UTR-IND-99990012",
            "created_at": "2026-08-01T12:05:00+00:00",
            "status": "SUCCESS",
        }
    ]
    settlements = [
        {
            "settlement_id": "SET-FZ-010",
            "utr": "UTR-IND-99990021",
            "amount": "1469.51",
            "fees": "29.99",
            "settled_at": "2026-08-02T12:05:00+00:00",
        }
    ]
    invoices = [{"invoice_id": "INV-FZ-010", "order_id": "ORD-FZ-001", "amount": "1499.50"}]

    matcher = FuzzyMatcher(orders, payments, settlements, invoices)
    res = matcher.match_order("ORD-FZ-001")

    ev = res.evidence
    assert isinstance(ev, FuzzyMatchEvidence)
    assert ev.candidate_payment_id == "PAY-FZ-010"
    assert ev.candidate_settlement_id == "SET-FZ-010"
    assert ev.amount_score == 1.0
    assert ev.reference_score >= 0.85
    assert ev.relationship_score == 1.0
    assert ev.date_score == 1.0
    assert ev.final_score >= 0.90
    assert ev.confidence_band == ConfidenceBand.HIGH.value
    assert len(ev.top_candidates) >= 1


def test_delayed_settlement_handling(base_order):
    """Test 11: Delayed settlement identifies the correct candidate but flags SLA breach."""
    orders = [base_order]
    payments = [
        {
            "payment_id": "PAY-FZ-011",
            "order_id": "ORD-FZ-001",
            "amount": "1499.50",
            "method": "UPI",
            "utr": "UTR-IND-99990011",
            "created_at": "2026-08-01T12:05:00+00:00",
            "status": "SUCCESS",
        }
    ]
    # 7 days delay (> 5 days SLA)
    settlements = [
        {
            "settlement_id": "SET-FZ-011",
            "utr": "UTR-IND-99990011",
            "amount": "1469.51",
            "fees": "29.99",
            "settled_at": "2026-08-08T12:05:00+00:00",
        }
    ]
    invoices = [{"invoice_id": "INV-FZ-011", "order_id": "ORD-FZ-001", "amount": "1499.50"}]

    matcher = FuzzyMatcher(orders, payments, settlements, invoices)
    res = matcher.match_order("ORD-FZ-001")

    # Correct candidate identified
    assert res.settlement_ids == ["SET-FZ-011"]
    assert res.status == MatchStatus.DISCREPANCY
    assert "exceeds 5-day SLA policy" in res.reason


def test_no_over_matching_on_operational_dataset():
    """Test 12: Verify fuzzy matcher resolves only expected fuzzy cases and avoids over-matching."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    matcher = FuzzyMatcher.from_csv_directory(data_dir)
    summary = matcher.get_summary()

    # Exact matches: 720
    assert summary["matched_exact"] == 720

    # Fuzzy matches should specifically resolve ROUNDING_MISMATCH (20) and REFERENCE_TYPO (20) = 40 cases
    assert summary["matched_fuzzy"] == 40

    # Total matched = 720 + 40 = 760 cases (76.0%)
    assert summary["matched_total"] == 760
    assert summary["matched_total_percentage"] == 76.0

    # Exactly 240 cases remain safely unresolved across non-matched categories
    assert summary["total_processed"] - summary["matched_total"] == 240
    assert summary["ambiguous"] in [80, 81]
    assert summary["unmatched"] in [44, 45]
    assert summary["discrepancy"] in [114, 115, 116]
