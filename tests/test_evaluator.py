"""Unit and integration tests for the ReconGuard ReconciliationEvaluator.

Tests all evaluation capabilities with focused, fast unit fixtures and verifies
ground truth isolation from production matching components.
"""

from decimal import Decimal
import ast
import json
from pathlib import Path
import pytest

from app.evaluation.evaluator import (
    ClassificationMetrics,
    EvaluationReport,
    LinkageMetrics,
    ReconciliationEvaluator,
    ResolutionMetrics,
    SafetyMetrics,
)
from app.matching.engine import ReconciliationEngine
from app.matching.types import ConfidenceBand, MatchMethod, MatchResult, MatchStatus


@pytest.fixture
def sample_ground_truth() -> list[dict]:
    """Provide a small synthetic ground truth fixture."""
    return [
        {
            "order_id": "ORD-001",
            "expected_scenario": "EXACT_MATCH",
            "expected_outcome": "MATCHED",
            "expected_resolution_class": "AUTO_RESOLVED",
            "linked_payment_ids": ["PAY-001"],
            "linked_settlement_ids": ["SET-001"],
            "expected_ai_investigation": False,
        },
        {
            "order_id": "ORD-002",
            "expected_scenario": "MULTI_ORDER_SETTLEMENT",
            "expected_outcome": "MATCHED",
            "expected_resolution_class": "AUTO_RESOLVED",
            "linked_payment_ids": ["PAY-002"],
            "linked_settlement_ids": ["SET-BATCH-01"],
            "expected_ai_investigation": False,
        },
        {
            "order_id": "ORD-003",
            "expected_scenario": "AMOUNT_MISMATCH",
            "expected_outcome": "DISCREPANCY_FOUND",
            "expected_resolution_class": "DETERMINISTIC_ESCALATION",
            "linked_payment_ids": ["PAY-003"],
            "linked_settlement_ids": ["SET-003"],
            "expected_ai_investigation": False,
        },
        {
            "order_id": "ORD-004",
            "expected_scenario": "MISSING_PAYMENT",
            "expected_outcome": "UNMATCHED",
            "expected_resolution_class": "DETERMINISTIC_ESCALATION",
            "linked_payment_ids": [],
            "linked_settlement_ids": [],
            "expected_ai_investigation": False,
        },
        {
            "order_id": "ORD-005",
            "expected_scenario": "ROUNDING_MISMATCH",
            "expected_outcome": "DISCREPANCY_FOUND",
            "expected_resolution_class": "AI_INVESTIGATION",
            "linked_payment_ids": ["PAY-005"],
            "linked_settlement_ids": ["SET-005"],
            "expected_ai_investigation": True,
        },
    ]


class TestEvaluatorComparisons:
    """Test individual evaluation comparison logic using synthetic data."""

    def test_correct_outcome_comparison(self, sample_ground_truth):
        """Test 1: Correct outcome comparison when engine output matches ground truth."""
        evaluator = ReconciliationEvaluator(ground_truth=sample_ground_truth)
        results = [
            MatchResult(
                order_id="ORD-001",
                status=MatchStatus.MATCHED,
                match_method=MatchMethod.EXACT,
                payment_ids=["PAY-001"],
                settlement_ids=["SET-001"],
            ),
            MatchResult(
                order_id="ORD-003",
                status=MatchStatus.DISCREPANCY,
                match_method=MatchMethod.NONE,
                payment_ids=["PAY-003"],
                settlement_ids=["SET-003"],
            ),
        ]
        clf = evaluator._evaluate_classification(results)
        assert clf.per_class["MATCHED"].precision == 1.0
        assert clf.per_class["MATCHED"].recall == 1.0
        assert clf.per_class["DISCREPANCY"].precision == 1.0

    def test_incorrect_outcome_comparison(self, sample_ground_truth):
        """Test 2: Incorrect outcome comparison when engine predicts mismatched status."""
        evaluator = ReconciliationEvaluator(ground_truth=sample_ground_truth)
        results = [
            MatchResult(
                order_id="ORD-003",  # Expected DISCREPANCY
                status=MatchStatus.MATCHED,  # Incorrectly predicted MATCHED
                match_method=MatchMethod.FUZZY,
                payment_ids=["PAY-003"],
                settlement_ids=["SET-003"],
            ),
        ]
        clf = evaluator._evaluate_classification(results)
        # DISCREPANCY has 1 support in GT, but was predicted as MATCHED -> Recall for DISCREPANCY is 0.0
        assert clf.per_class["DISCREPANCY"].recall == 0.0
        assert clf.per_class["MATCHED"].precision == 0.0

    def test_exact_payment_linkage(self, sample_ground_truth):
        """Test 3: Exact payment linkage accuracy calculation."""
        evaluator = ReconciliationEvaluator(ground_truth=sample_ground_truth)
        results = [
            MatchResult(order_id="ORD-001", status=MatchStatus.MATCHED, match_method=MatchMethod.EXACT, payment_ids=["PAY-001"]),
            MatchResult(order_id="ORD-002", status=MatchStatus.MATCHED, match_method=MatchMethod.AGGREGATION, payment_ids=["PAY-002"]),
        ]
        linkage = evaluator._evaluate_payment_linkage(results)
        assert linkage.total_cases == 2
        assert linkage.exact_set_matches == 2
        assert linkage.exact_set_accuracy == 1.0
        assert linkage.precision == 1.0
        assert linkage.recall == 1.0

    def test_partial_payment_linkage(self):
        """Test 4: Partial payment linkage where 1 of 2 expected payments is missing."""
        gt = [{
            "order_id": "ORD-100",
            "expected_scenario": "AMBIGUOUS_CANDIDATE",
            "expected_outcome": "DISCREPANCY_FOUND",
            "linked_payment_ids": ["PAY-A", "PAY-B"],
            "linked_settlement_ids": [],
        }]
        evaluator = ReconciliationEvaluator(ground_truth=gt)
        results = [
            MatchResult(order_id="ORD-100", status=MatchStatus.AMBIGUOUS, match_method=MatchMethod.NONE, payment_ids=["PAY-A"]),
        ]
        linkage = evaluator._evaluate_payment_linkage(results)
        assert linkage.exact_set_matches == 0
        assert linkage.true_positives == 1
        assert linkage.false_negatives == 1
        assert linkage.precision == 1.0
        assert linkage.recall == 0.5

    def test_extra_predicted_payment(self):
        """Test 5: Extra predicted payment generates false positive in linkage."""
        gt = [{
            "order_id": "ORD-101",
            "expected_scenario": "EXACT_MATCH",
            "expected_outcome": "MATCHED",
            "linked_payment_ids": ["PAY-A"],
            "linked_settlement_ids": [],
        }]
        evaluator = ReconciliationEvaluator(ground_truth=gt)
        results = [
            MatchResult(order_id="ORD-101", status=MatchStatus.MATCHED, match_method=MatchMethod.EXACT, payment_ids=["PAY-A", "PAY-EXTRA"]),
        ]
        linkage = evaluator._evaluate_payment_linkage(results)
        assert linkage.exact_set_matches == 0
        assert linkage.true_positives == 1
        assert linkage.false_positives == 1
        assert linkage.precision == 0.5
        assert linkage.recall == 1.0

    def test_empty_expected_and_predicted_linkage(self, sample_ground_truth):
        """Test 6: Empty expected and empty predicted linkage is a correct set match."""
        evaluator = ReconciliationEvaluator(ground_truth=sample_ground_truth)
        results = [
            MatchResult(order_id="ORD-004", status=MatchStatus.UNMATCHED, match_method=MatchMethod.NONE, payment_ids=[], settlement_ids=[]),
        ]
        linkage_p = evaluator._evaluate_payment_linkage(results)
        linkage_s = evaluator._evaluate_settlement_linkage(results)
        assert linkage_p.exact_set_matches == 1
        assert linkage_p.exact_set_accuracy == 1.0
        assert linkage_p.false_positives == 0
        assert linkage_s.exact_set_matches == 1
        assert linkage_s.exact_set_accuracy == 1.0

    def test_multi_payment_linkage(self):
        """Test 7: Complete set matching for multi-payment cases."""
        gt = [{
            "order_id": "ORD-200",
            "expected_scenario": "DUPLICATE_PAYMENT",
            "expected_outcome": "DISCREPANCY_FOUND",
            "linked_payment_ids": ["PAY-01", "PAY-02", "PAY-03"],
            "linked_settlement_ids": [],
        }]
        evaluator = ReconciliationEvaluator(ground_truth=gt)
        # Order of elements in list should not matter (set comparison)
        results = [
            MatchResult(order_id="ORD-200", status=MatchStatus.AMBIGUOUS, match_method=MatchMethod.DUPLICATE, payment_ids=["PAY-03", "PAY-01", "PAY-02"]),
        ]
        linkage = evaluator._evaluate_payment_linkage(results)
        assert linkage.exact_set_matches == 1
        assert linkage.precision == 1.0
        assert linkage.recall == 1.0
        assert linkage.f1 == 1.0

    def test_multi_settlement_linkage(self):
        """Test 8: Complete set matching for multi-settlement cases."""
        gt = [{
            "order_id": "ORD-300",
            "expected_scenario": "MULTI_SETTLEMENT",
            "expected_outcome": "MATCHED",
            "linked_payment_ids": ["PAY-300"],
            "linked_settlement_ids": ["SET-A", "SET-B"],
        }]
        evaluator = ReconciliationEvaluator(ground_truth=gt)
        results = [
            MatchResult(order_id="ORD-300", status=MatchStatus.MATCHED, match_method=MatchMethod.AGGREGATION, payment_ids=["PAY-300"], settlement_ids=["SET-B", "SET-A"]),
        ]
        linkage = evaluator._evaluate_settlement_linkage(results)
        assert linkage.exact_set_matches == 1
        assert linkage.precision == 1.0
        assert linkage.recall == 1.0

    def test_scenario_aggregation(self, sample_ground_truth):
        """Test 9: Scenario-level grouping and metric aggregation."""
        evaluator = ReconciliationEvaluator(ground_truth=sample_ground_truth)
        results = [
            MatchResult(order_id="ORD-001", status=MatchStatus.MATCHED, match_method=MatchMethod.EXACT, payment_ids=["PAY-001"], settlement_ids=["SET-001"]),
            MatchResult(order_id="ORD-002", status=MatchStatus.MATCHED, match_method=MatchMethod.AGGREGATION, payment_ids=["PAY-002"], settlement_ids=["SET-BATCH-01"]),
            MatchResult(order_id="ORD-003", status=MatchStatus.DISCREPANCY, match_method=MatchMethod.NONE, payment_ids=["PAY-003"], settlement_ids=["SET-003"]),
            MatchResult(order_id="ORD-004", status=MatchStatus.UNMATCHED, match_method=MatchMethod.NONE, payment_ids=[], settlement_ids=[]),
            MatchResult(order_id="ORD-005", status=MatchStatus.MATCHED, match_method=MatchMethod.FUZZY, payment_ids=["PAY-005"], settlement_ids=["SET-005"]),
        ]
        scenarios = evaluator._evaluate_scenarios(results)
        assert len(scenarios) == 5
        assert scenarios["EXACT_MATCH"].correct_outcomes == 1
        assert scenarios["MULTI_ORDER_SETTLEMENT"].correctly_resolved_cases == 1
        assert scenarios["ROUNDING_MISMATCH"].false_matches == 1

    def test_false_match_calculation(self, sample_ground_truth):
        """Test 10: False-match count and rates against financial safety definitions."""
        evaluator = ReconciliationEvaluator(ground_truth=sample_ground_truth)
        # ORD-005 is ROUNDING_MISMATCH with expected_outcome DISCREPANCY_FOUND & AI_INVESTIGATION.
        # If predicted as MATCHED, it counts as a false match.
        results = [
            MatchResult(order_id="ORD-001", status=MatchStatus.MATCHED, match_method=MatchMethod.EXACT),
            MatchResult(order_id="ORD-005", status=MatchStatus.MATCHED, match_method=MatchMethod.FUZZY),
        ]
        safety = evaluator._evaluate_safety(results)
        assert safety.false_match_count == 1
        assert safety.false_match_rate_total == 0.5  # 1 / 2
        assert safety.false_match_rate_matches == 0.5  # 1 / 2

    def test_deterministic_resolution_evaluation(self, sample_ground_truth):
        """Test 11: Resolution metrics separate resolved from correctly resolved."""
        evaluator = ReconciliationEvaluator(ground_truth=sample_ground_truth)
        results = [
            MatchResult(order_id="ORD-001", status=MatchStatus.MATCHED, match_method=MatchMethod.EXACT, payment_ids=["PAY-001"], settlement_ids=["SET-001"]),
            MatchResult(order_id="ORD-005", status=MatchStatus.MATCHED, match_method=MatchMethod.FUZZY, payment_ids=["PAY-005"], settlement_ids=["SET-005"]),
            MatchResult(order_id="ORD-003", status=MatchStatus.DISCREPANCY, match_method=MatchMethod.NONE, payment_ids=["PAY-003"], settlement_ids=["SET-003"]),
        ]
        res = evaluator._evaluate_resolution(results)
        assert res.total_cases == 3
        assert res.resolved_cases == 2
        assert res.correctly_resolved_cases == 1
        assert res.incorrectly_resolved_cases == 1
        assert res.unresolved_cases == 1
        assert res.deterministic_resolution_rate == round(2 / 3, 4)
        assert res.resolution_correctness_rate == 0.5

    def test_ground_truth_isolation(self):
        """Test 12: Ensure matching modules never import ground truth or evaluation logic."""
        import app.matching.aggregation_matcher as agg_mod
        import app.matching.duplicate_detector as dup_mod
        import app.matching.engine as eng_mod
        import app.matching.exact_matcher as exact_mod
        import app.matching.fuzzy_matcher as fuzzy_mod
        import app.matching.types as types_mod

        matching_modules = [agg_mod, dup_mod, eng_mod, exact_mod, fuzzy_mod, types_mod]

        for mod in matching_modules:
            src = Path(mod.__file__).read_text(encoding="utf-8")
            tree = ast.parse(src)
            # Check all imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "evaluation" not in alias.name, f"Forbidden import {alias.name} in {mod.__file__}"
                        assert "ground_truth" not in alias.name, f"Forbidden import {alias.name} in {mod.__file__}"
                elif isinstance(node, ast.ImportFrom):
                    mod_name = node.module or ""
                    assert "evaluation" not in mod_name, f"Forbidden from-import {mod_name} in {mod.__file__}"
                    assert "ground_truth" not in mod_name, f"Forbidden from-import {mod_name} in {mod.__file__}"

            # Check that string literals containing ground truth paths do not exist in matching code
            assert "ground_truth.csv" not in src, f"Ground truth filename referenced in {mod.__file__}"
            assert "ground_truth.json" not in src, f"Ground truth filename referenced in {mod.__file__}"


class TestEvaluatorFullRun:
    """Integration test running the complete 1,000-case evaluation."""

    def test_full_dataset_evaluation(self):
        """Run full evaluation on 1,000 cases and verify benchmark sanity."""
        evaluator = ReconciliationEvaluator.from_directories("data")
        report = evaluator.evaluate()

        assert report.total_cases == 1000
        assert report.resolution.resolved_cases == 820
        assert report.resolution.correctly_resolved_cases == 780
        assert report.resolution.unresolved_cases == 180
        assert report.resolution.resolution_coverage_recall == 1.0
        assert report.safety.false_match_count == 40
        assert report.payment_linkage.exact_set_matches == 1000
        assert report.settlement_linkage.exact_set_matches == 907
        assert report.aggregation.total_aggregation_cases == 60
        assert report.aggregation.correctly_classified == 60
        assert report.aggregation.exact_payment_linkage_count == 60
        assert report.aggregation.exact_settlement_linkage_count == 60
        assert report.aggregation.false_aggregation_count == 0
        assert len(report.scenarios) == 13
        assert report.discrepancy_analysis["order_id"] == "ORD-000992"
        assert report.runtime_seconds < 5.0

