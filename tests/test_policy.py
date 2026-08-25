"""Unit and integration tests for the ReconGuard Policy & Exception Orchestration Layer.

Tests all 17 requirements:
1. Exact match -> AUTO_RESOLVE
2. Aggregation match -> AUTO_RESOLVE
3. Rounding mismatch -> AI_INVESTIGATION
4. Reference typo -> AI_INVESTIGATION
5. Missing invoice -> AI_INVESTIGATION
6. Amount mismatch -> ESCALATE
7. Refund -> ESCALATE
8. Chargeback -> ESCALATE
9. Ambiguous candidate -> HUMAN_REVIEW
10. Insufficient evidence -> HUMAN_REVIEW
11. Missing settlement -> ESCALATE
12. Priority calculation
13. Financial impact preservation
14. Explainability
15. Determinism
16. Ground-truth isolation
17. No mutation of Master Engine results
"""

import ast
import copy
from pathlib import Path
import pytest

from app.matching.engine import ReconciliationEngine
from app.matching.types import (
    ConfidenceBand,
    ExactMatchEvidence,
    FuzzyMatchEvidence,
    MatchMethod,
    MatchResult,
    MatchStatus,
)
from app.policy.engine import PolicyEngine
from app.policy.queue import ExceptionQueue
from app.policy.types import (
    CasePriority,
    ExceptionCase,
    ExceptionType,
    PolicyDecision,
)


@pytest.fixture
def policy_engine() -> PolicyEngine:
    return PolicyEngine()


class TestPolicyRules:
    """Test policy engine rule evaluations using focused unit fixtures."""

    def test_exact_match_auto_resolve(self, policy_engine):
        """Test 1: Exact match -> AUTO_RESOLVE with LOW priority."""
        res = MatchResult(
            order_id="ORD-000001",
            status=MatchStatus.MATCHED,
            match_method=MatchMethod.EXACT,
            payment_ids=["PAY-000001"],
            settlement_ids=["SET-000001"],
            invoice_id="INV-000001",
            confidence=1.0,
            financial_impact=0.0,
            reason="Exact 1:1 match verified across order, payment, settlement, and invoice within SLA",
        )
        case = policy_engine.evaluate(res)
        assert case.decision == PolicyDecision.AUTO_RESOLVE
        assert case.exception_type == ExceptionType.NONE
        assert case.priority == CasePriority.LOW
        assert not case.requires_ai
        assert not case.requires_human
        assert "straight-through" in case.explanation.lower()

    def test_aggregation_match_auto_resolve(self, policy_engine):
        """Test 2: Multi-order aggregation match -> AUTO_RESOLVE with LOW priority."""
        res = MatchResult(
            order_id="ORD-000721",
            status=MatchStatus.MATCHED,
            match_method=MatchMethod.AGGREGATION,
            payment_ids=["PAY-000721"],
            settlement_ids=["SET-BATCH-0001"],
            invoice_id="INV-000721",
            confidence=1.0,
            financial_impact=0.0,
            reason="Order reconciled as part of multi-order settlement batch SET-BATCH-0001",
        )
        case = policy_engine.evaluate(res)
        assert case.decision == PolicyDecision.AUTO_RESOLVE
        assert case.exception_type == ExceptionType.NONE
        assert case.priority == CasePriority.LOW
        assert not case.requires_ai
        assert not case.requires_human
        assert "batch" in case.explanation.lower()

    def test_rounding_mismatch_ai_investigation(self, policy_engine):
        """Test 3: Rounding mismatch -> AI_INVESTIGATION with ROUNDING_VARIANCE."""
        ev = FuzzyMatchEvidence(
            amount_difference=0.05,
            reference_similarity=1.0,
            candidate_payment_id="PAY-000877",
            candidate_settlement_id="SET-000837",
        )
        res = MatchResult(
            order_id="ORD-000901",
            status=MatchStatus.MATCHED,
            match_method=MatchMethod.FUZZY,
            payment_ids=["PAY-000877"],
            settlement_ids=["SET-000837"],
            invoice_id="INV-000901",
            confidence=0.9996,
            financial_impact=0.05,
            evidence=ev,
            reason="Fuzzy match verified with HIGH confidence (1.00); reference similarity 1.00, amount diff INR 0.05",
        )
        case = policy_engine.evaluate(res)
        assert case.decision == PolicyDecision.AI_INVESTIGATION
        assert case.exception_type == ExceptionType.ROUNDING_VARIANCE
        assert case.priority == CasePriority.LOW
        assert case.requires_ai
        assert not case.requires_human
        assert case.financial_impact == 0.05

    def test_reference_typo_ai_investigation(self, policy_engine):
        """Test 4: Reference typo -> AI_INVESTIGATION with REFERENCE_MISMATCH."""
        ev = FuzzyMatchEvidence(
            amount_difference=0.0,
            reference_similarity=0.9375,
            candidate_payment_id="PAY-000897",
            candidate_settlement_id="SET-000857",
        )
        res = MatchResult(
            order_id="ORD-000921",
            status=MatchStatus.MATCHED,
            match_method=MatchMethod.FUZZY,
            payment_ids=["PAY-000897"],
            settlement_ids=["SET-000857"],
            invoice_id="INV-000921",
            confidence=0.9813,
            financial_impact=0.0,
            evidence=ev,
            reason="Fuzzy match verified with HIGH confidence (0.98); reference similarity 0.94, amount diff INR 0.00",
        )
        case = policy_engine.evaluate(res)
        assert case.decision == PolicyDecision.AI_INVESTIGATION
        assert case.exception_type == ExceptionType.REFERENCE_MISMATCH
        assert case.priority == CasePriority.MEDIUM
        assert case.requires_ai
        assert not case.requires_human

    def test_missing_invoice_ai_investigation(self, policy_engine):
        """Test 5: Missing invoice -> AI_INVESTIGATION with MISSING_INVOICE."""
        ev = FuzzyMatchEvidence(
            failed_checks=["invoice_exists"],
            amount_difference=0.0,
            reference_similarity=1.0,
        )
        res = MatchResult(
            order_id="ORD-000941",
            status=MatchStatus.DISCREPANCY,
            match_method=MatchMethod.FUZZY,
            payment_ids=["PAY-000917"],
            settlement_ids=["SET-000877"],
            invoice_id=None,
            confidence=1.0,
            financial_impact=0.0,
            evidence=ev,
            reason="High-confidence fuzzy match found (1.00), but invoice record is missing for order",
        )
        case = policy_engine.evaluate(res)
        assert case.decision == PolicyDecision.AI_INVESTIGATION
        assert case.exception_type == ExceptionType.MISSING_INVOICE
        assert case.priority == CasePriority.MEDIUM
        assert case.requires_ai
        assert not case.requires_human

    def test_amount_mismatch_escalate(self, policy_engine):
        """Test 6: Amount mismatch -> ESCALATE with AMOUNT_MISMATCH and HIGH priority."""
        ev = ExactMatchEvidence(
            failed_checks=["payment_amount_match"],
            amount_difference=1500.0,
        )
        res = MatchResult(
            order_id="ORD-000781",
            status=MatchStatus.DISCREPANCY,
            match_method=MatchMethod.NONE,
            payment_ids=["PAY-000781"],
            settlement_ids=[],
            invoice_id=None,
            confidence=0.3,
            financial_impact=1500.0,
            evidence=ev,
            reason="Large amount mismatch: order INR 4999.00 vs payment INR 3499.00",
        )
        case = policy_engine.evaluate(res)
        assert case.decision == PolicyDecision.ESCALATE
        assert case.exception_type == ExceptionType.AMOUNT_MISMATCH
        assert case.priority == CasePriority.HIGH
        assert not case.requires_ai
        assert case.requires_human
        assert case.financial_impact == 1500.0

    def test_refund_escalate(self, policy_engine):
        """Test 7: Refund -> ESCALATE with REFUND and HIGH priority."""
        ev = ExactMatchEvidence(
            failed_checks=["no_adjustments_present"],
            adjustment_ids=["ADJ-000025"],
            adjustment_types=["REFUND"],
        )
        res = MatchResult(
            order_id="ORD-000877",
            status=MatchStatus.DISCREPANCY,
            match_method=MatchMethod.NONE,
            payment_ids=["PAY-000853"],
            settlement_ids=[],
            invoice_id=None,
            adjustment_ids=["ADJ-000025"],
            confidence=0.0,
            financial_impact=49999.0,
            evidence=ev,
            reason="Active adjustments (REFUND) logged against transaction",
        )
        case = policy_engine.evaluate(res)
        assert case.decision == PolicyDecision.ESCALATE
        assert case.exception_type == ExceptionType.REFUND
        assert case.priority == CasePriority.HIGH
        assert not case.requires_ai
        assert case.requires_human
        assert case.financial_impact == 49999.0

    def test_chargeback_escalate(self, policy_engine):
        """Test 8: Chargeback -> ESCALATE with CHARGEBACK and HIGH priority."""
        ev = ExactMatchEvidence(
            failed_checks=["no_adjustments_present"],
            adjustment_ids=["ADJ-000001"],
            adjustment_types=["CHARGEBACK"],
        )
        res = MatchResult(
            order_id="ORD-000853",
            status=MatchStatus.DISCREPANCY,
            match_method=MatchMethod.NONE,
            payment_ids=["PAY-000829"],
            settlement_ids=[],
            invoice_id=None,
            adjustment_ids=["ADJ-000001"],
            confidence=0.0,
            financial_impact=2499.0,
            evidence=ev,
            reason="Active adjustments (CHARGEBACK) logged against transaction",
        )
        case = policy_engine.evaluate(res)
        assert case.decision == PolicyDecision.ESCALATE
        assert case.exception_type == ExceptionType.CHARGEBACK
        assert case.priority == CasePriority.HIGH
        assert not case.requires_ai
        assert case.requires_human
        assert case.financial_impact == 2499.0

    def test_ambiguous_candidate_human_review(self, policy_engine):
        """Test 9: Ambiguous retry candidate payments -> HUMAN_REVIEW."""
        res = MatchResult(
            order_id="ORD-000951",
            status=MatchStatus.AMBIGUOUS,
            match_method=MatchMethod.NONE,
            payment_ids=["PAY-000927", "PAY-000928"],
            settlement_ids=[],
            invoice_id=None,
            confidence=0.7,
            financial_impact=2499.0,
            reason="Multiple (2) candidate payments with distinct references found on order ORD-000951; customer retry attempt",
        )
        case = policy_engine.evaluate(res)
        assert case.decision == PolicyDecision.HUMAN_REVIEW
        assert case.exception_type == ExceptionType.AMBIGUOUS_CANDIDATE
        assert case.priority == CasePriority.HIGH
        assert not case.requires_ai
        assert case.requires_human
        assert len(case.payment_ids) == 2

    def test_insufficient_evidence_human_review(self, policy_engine):
        """Test 10: Abandoned order with insufficient evidence -> HUMAN_REVIEW."""
        ev = ExactMatchEvidence(
            failed_checks=["order_completed_status"],
            order_status="ABANDONED",
        )
        res = MatchResult(
            order_id="ORD-000971",
            status=MatchStatus.UNMATCHED,
            match_method=MatchMethod.NONE,
            payment_ids=[],
            settlement_ids=[],
            invoice_id=None,
            confidence=0.0,
            financial_impact=9999.0,
            evidence=ev,
            reason="Order status is 'ABANDONED' (not COMPLETED)",
        )
        case = policy_engine.evaluate(res)
        assert case.decision == PolicyDecision.HUMAN_REVIEW
        assert case.exception_type == ExceptionType.INSUFFICIENT_EVIDENCE
        assert case.priority == CasePriority.HIGH
        assert not case.requires_ai
        assert case.requires_human

    def test_missing_settlement_escalate(self, policy_engine):
        """Test 11: Missing bank settlement payout -> ESCALATE."""
        ev = ExactMatchEvidence(
            failed_checks=["settlement_exists"],
        )
        res = MatchResult(
            order_id="ORD-000992",
            status=MatchStatus.DISCREPANCY,
            match_method=MatchMethod.NONE,
            payment_ids=["PAY-000968"],
            settlement_ids=[],
            invoice_id=None,
            confidence=0.0,
            financial_impact=14999.0,
            evidence=ev,
            reason="No bank settlement found matching UTR 'UTR-IND-00000992'",
        )
        case = policy_engine.evaluate(res)
        assert case.decision == PolicyDecision.ESCALATE
        assert case.exception_type == ExceptionType.MISSING_SETTLEMENT
        assert case.priority == CasePriority.HIGH
        assert not case.requires_ai
        assert case.requires_human

    def test_priority_calculation(self, policy_engine):
        """Test 12: Configurable priority thresholds and risk attribution."""
        # Low impact rounding -> LOW
        low_res = MatchResult(
            order_id="ORD-LOW",
            status=MatchStatus.MATCHED,
            match_method=MatchMethod.FUZZY,
            evidence=FuzzyMatchEvidence(amount_difference=0.10, reference_similarity=1.0),
            financial_impact=0.10,
        )
        assert policy_engine.evaluate(low_res).priority == CasePriority.LOW

        # High impact dispute -> HIGH
        high_res = MatchResult(
            order_id="ORD-HIGH",
            status=MatchStatus.DISCREPANCY,
            match_method=MatchMethod.NONE,
            reason="Active adjustments (CHARGEBACK)",
            financial_impact=10000.0,
        )
        assert policy_engine.evaluate(high_res).priority == CasePriority.HIGH

    def test_financial_impact_preservation(self, policy_engine):
        """Test 13: Financial exposure amount is preserved accurately from MatchResult."""
        res = MatchResult(
            order_id="ORD-FIN",
            status=MatchStatus.DISCREPANCY,
            match_method=MatchMethod.NONE,
            reason="Large amount mismatch",
            financial_impact=12345.67,
        )
        case = policy_engine.evaluate(res)
        assert case.financial_impact == 12345.67

    def test_explainability(self, policy_engine):
        """Test 14: Every decision generates human-auditable explanations and next actions."""
        res = MatchResult(
            order_id="ORD-EXP",
            status=MatchStatus.DISCREPANCY,
            match_method=MatchMethod.NONE,
            reason="No captured payment record found for order",
            financial_impact=7500.0,
        )
        case = policy_engine.evaluate(res)
        assert len(case.explanation) > 10
        assert len(case.next_action) > 10
        assert "gateway" in case.next_action.lower() or "payment" in case.next_action.lower()

    def test_determinism(self, policy_engine):
        """Test 15: Policy evaluation is strictly deterministic across repeated invocations."""
        res = MatchResult(
            order_id="ORD-DET",
            status=MatchStatus.MATCHED,
            match_method=MatchMethod.EXACT,
            payment_ids=["PAY-01"],
            settlement_ids=["SET-01"],
            invoice_id="INV-01",
            confidence=1.0,
        )
        case1 = policy_engine.evaluate(res)
        case2 = policy_engine.evaluate(res)
        assert case1.decision == case2.decision
        assert case1.exception_type == case2.exception_type
        assert case1.priority == case2.priority
        assert case1.explanation == case2.explanation

    def test_ground_truth_isolation(self):
        """Test 16: Ensure policy module never imports ground truth or evaluation logic."""
        import app.policy.engine as eng_mod
        import app.policy.queue as queue_mod
        import app.policy.types as types_mod

        for mod in [eng_mod, queue_mod, types_mod]:
            src = Path(mod.__file__).read_text(encoding="utf-8")
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "ground_truth" not in alias.name
                        assert "evaluation" not in alias.name
                elif isinstance(node, ast.ImportFrom):
                    mod_name = node.module or ""
                    assert "ground_truth" not in mod_name
                    assert "evaluation" not in mod_name
            assert "ground_truth.csv" not in src
            assert "ground_truth.json" not in src

    def test_no_mutation_of_master_engine_results(self, policy_engine):
        """Test 17: PolicyEngine does not mutate input MatchResult objects."""
        orig_res = MatchResult(
            order_id="ORD-MUT",
            status=MatchStatus.MATCHED,
            match_method=MatchMethod.EXACT,
            payment_ids=["PAY-01"],
            settlement_ids=["SET-01"],
            invoice_id="INV-01",
            confidence=1.0,
            financial_impact=0.0,
            reason="Original reason",
        )
        res_copy = copy.deepcopy(orig_res)
        policy_engine.evaluate(orig_res)
        assert orig_res == res_copy


class TestExceptionQueueIntegration:
    """Test ExceptionQueue indexing, querying, and full dataset execution."""

    def test_full_1000_dataset_policy_execution(self):
        """Execute complete pipeline across 1,000 cases and verify strict invariants."""
        engine = ReconciliationEngine.from_csv_directory("data")
        match_results = engine.reconcile_all()
        assert len(match_results) == 1000

        queue = ExceptionQueue.from_engine_results(match_results)
        assert queue.total_count == 1000

        summary = queue.get_summary()

        # Decision distribution must strictly equal 1,000
        dec_counts = summary["decision_counts"]
        assert dec_counts["AUTO_RESOLVE"] == 780
        assert dec_counts["AI_INVESTIGATION"] == 50
        assert dec_counts["HUMAN_REVIEW"] == 40
        assert dec_counts["ESCALATE"] == 130
        assert sum(dec_counts.values()) == 1000

        # Query helper tests
        assert len(queue.get_auto_resolve_cases()) == 780
        assert len(queue.get_ai_investigation_cases()) == 50
        assert len(queue.get_human_review_cases()) == 40
        assert len(queue.get_escalations()) == 130
        assert len(queue.get_high_priority_cases()) == 170

        # Exception types
        ext_counts = summary["exception_type_counts"]
        assert ext_counts["NONE"] == 780
        assert ext_counts["ROUNDING_VARIANCE"] == 20
        assert ext_counts["REFERENCE_MISMATCH"] == 20
        assert ext_counts["MISSING_INVOICE"] == 10
        assert ext_counts["AMOUNT_MISMATCH"] == 24
        assert ext_counts["SLA_BREACH"] == 24
        assert ext_counts["MISSING_PAYMENT"] == 24
        assert ext_counts["CHARGEBACK"] == 24
        assert ext_counts["REFUND"] == 24
        assert ext_counts["AMBIGUOUS_CANDIDATE"] == 20
        assert ext_counts["INSUFFICIENT_EVIDENCE"] == 20
        assert ext_counts["MISSING_SETTLEMENT"] == 10

        # Verify lookup by order_id and case_id
        case_001 = queue.get_case_by_order_id("ORD-000001")
        assert case_001 is not None
        assert case_001.case_id == "CASE-000001"
        assert case_001.decision == PolicyDecision.AUTO_RESOLVE

        case_901 = queue.get_case_by_order_id("ORD-000901")
        assert case_901 is not None
        assert case_901.decision == PolicyDecision.AI_INVESTIGATION
        assert case_901.exception_type == ExceptionType.ROUNDING_VARIANCE

