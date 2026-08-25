"""Unit and integration tests for the ReconGuard AI Investigator.

Tests all requirements:
1. rounding investigation
2. reference typo investigation
3. missing invoice investigation
4. contradictory evidence (chargeback/refund)
5. missing evidence (no payments found)
6. max tool-call limit (loop safety)
7. invalid tool request handling
8. unknown order handling
9. read-only behavior (no mutation)
10. structured output validation
11. confidence validation (0.0 - 1.0)
12. audit trace recording
13. deterministic mock provider
14. ground-truth isolation (no ground-truth imports)
15. no financial side effects
16. missing API key does not break tests
17. explicit safety recommendation language enforcement
18. 50-case AI evaluation benchmark run
"""

import ast
import os
from pathlib import Path
import pytest

from app.investigator.agent import InvestigatorAgent
from app.investigator.evaluator import AIEvaluator
from app.investigator.providers import GeminiProvider, MockProvider
from app.investigator.tools import InvestigationToolRegistry
from app.investigator.types import (
    FindingTaxonomy,
    InvestigationContext,
    InvestigationResult,
    InvestigationStatus,
)
from app.policy.types import CasePriority, ExceptionCase, ExceptionType, PolicyDecision


@pytest.fixture
def mock_tools() -> InvestigationToolRegistry:
    """Create in-memory tool registry with synthetic test data."""
    orders = [
        {"order_id": "ORD-RND", "amount": "1000.00", "currency": "INR", "status": "COMPLETED", "created_at": "2026-08-01T10:00:00Z"},
        {"order_id": "ORD-TYP", "amount": "2500.00", "currency": "INR", "status": "COMPLETED", "created_at": "2026-08-01T10:00:00Z"},
        {"order_id": "ORD-INV", "amount": "3000.00", "currency": "INR", "status": "COMPLETED", "created_at": "2026-08-01T10:00:00Z"},
        {"order_id": "ORD-CONTRADICT", "amount": "4000.00", "currency": "INR", "status": "COMPLETED", "created_at": "2026-08-01T10:00:00Z"},
        {"order_id": "ORD-NOPAY", "amount": "5000.00", "currency": "INR", "status": "COMPLETED", "created_at": "2026-08-01T10:00:00Z"},
    ]
    payments = [
        {"payment_id": "PAY-RND", "order_id": "ORD-RND", "amount": "1000.00", "currency": "INR", "status": "CAPTURED", "utr": "UTR-111", "created_at": "2026-08-01T10:01:00Z"},
        {"payment_id": "PAY-TYP", "order_id": "ORD-TYP", "amount": "2500.00", "currency": "INR", "status": "CAPTURED", "utr": "UTR-ABCD12", "created_at": "2026-08-01T10:01:00Z"},
        {"payment_id": "PAY-INV", "order_id": "ORD-INV", "amount": "3000.00", "currency": "INR", "status": "CAPTURED", "utr": "UTR-333", "created_at": "2026-08-01T10:01:00Z"},
        {"payment_id": "PAY-CONTRADICT", "order_id": "ORD-CONTRADICT", "amount": "4000.00", "currency": "INR", "status": "CAPTURED", "utr": "UTR-444", "created_at": "2026-08-01T10:01:00Z"},
    ]
    settlements = [
        {"settlement_id": "SET-RND", "payment_id": "PAY-RND", "amount": "1000.00", "fee": "20.00", "tax": "3.60", "utr": "UTR-111", "status": "SETTLED", "settled_at": "2026-08-02T10:00:00Z"},
        {"settlement_id": "SET-TYP", "payment_id": "PAY-TYP", "amount": "2500.00", "fee": "50.00", "tax": "9.00", "utr": "UTR-ABCD21", "status": "SETTLED", "settled_at": "2026-08-02T10:00:00Z"},
        {"settlement_id": "SET-INV", "payment_id": "PAY-INV", "amount": "3000.00", "fee": "60.00", "tax": "10.80", "utr": "UTR-333", "status": "SETTLED", "settled_at": "2026-08-02T10:00:00Z"},
        {"settlement_id": "SET-CONTRADICT", "payment_id": "PAY-CONTRADICT", "amount": "4000.00", "fee": "80.00", "tax": "14.40", "utr": "UTR-444", "status": "SETTLED", "settled_at": "2026-08-02T10:00:00Z"},
    ]
    invoices = [
        {"invoice_id": "INV-RND", "order_id": "ORD-RND", "amount": "1000.05", "tax_amount": "180.05", "status": "ISSUED", "created_at": "2026-08-01T10:00:00Z"},
        {"invoice_id": "INV-TYP", "order_id": "ORD-TYP", "amount": "2500.00", "tax_amount": "450.00", "status": "ISSUED", "created_at": "2026-08-01T10:00:00Z"},
        # ORD-INV has no invoice
    ]
    adjustments = [
        {"adjustment_id": "ADJ-01", "type": "CHARGEBACK", "amount": "4000.00", "related_id": "PAY-CONTRADICT", "reason": "Customer dispute", "created_at": "2026-08-03T10:00:00Z"},
    ]

    return InvestigationToolRegistry(
        orders=orders,
        payments=payments,
        settlements=settlements,
        invoices=invoices,
        adjustments=adjustments,
    )


@pytest.fixture
def agent(mock_tools) -> InvestigatorAgent:
    return InvestigatorAgent(tools=mock_tools, provider=MockProvider())


class TestInvestigatorAgentRules:
    """Test AI Investigator core investigation capabilities."""

    def test_rounding_investigation(self, agent):
        """Test 1: Rounding mismatch is verified with advisory recommendation."""
        ctx = InvestigationContext(
            case_id="CASE-RND",
            order_id="ORD-RND",
            exception_type="ROUNDING_VARIANCE",
            policy_decision="AI_INVESTIGATION",
            priority="LOW",
            financial_impact=0.05,
            payment_ids=["PAY-RND"],
            settlement_ids=["SET-RND"],
            reason="Fuzzy match verified with HIGH confidence; amount diff INR 0.05",
        )
        res = agent.investigate(ctx)
        assert res.finding == FindingTaxonomy.VERIFIED_ROUNDING_VARIANCE
        assert res.confidence >= 0.95
        assert not res.requires_human_review
        assert "no financial action was taken by the investigator" in res.recommendation.lower()
        assert "recommend reconciliation" in res.recommendation.lower()
        assert len(res.tool_trace) >= 4

    def test_reference_typo_investigation(self, agent):
        """Test 2: Reference typo is verified with advisory linkage recommendation."""
        ctx = InvestigationContext(
            case_id="CASE-TYP",
            order_id="ORD-TYP",
            exception_type="REFERENCE_MISMATCH",
            policy_decision="AI_INVESTIGATION",
            priority="MEDIUM",
            financial_impact=0.0,
            payment_ids=["PAY-TYP"],
            settlement_ids=["SET-TYP"],
            reason="Fuzzy match verified with reference similarity 0.94",
        )
        res = agent.investigate(ctx)
        assert res.finding == FindingTaxonomy.VERIFIED_REFERENCE_TYPO
        assert res.confidence >= 0.95
        assert not res.requires_human_review
        assert "no financial action was taken by the investigator" in res.recommendation.lower()
        assert "recommend linking" in res.recommendation.lower()

    def test_missing_invoice_investigation(self, agent):
        """Test 3: Missing invoice is confirmed with advisory backfill recommendation."""
        ctx = InvestigationContext(
            case_id="CASE-INV",
            order_id="ORD-INV",
            exception_type="MISSING_INVOICE",
            policy_decision="AI_INVESTIGATION",
            priority="MEDIUM",
            financial_impact=0.0,
            payment_ids=["PAY-INV"],
            settlement_ids=["SET-INV"],
            reason="Payment and settlement corroborated, but invoice is missing",
        )
        res = agent.investigate(ctx)
        assert res.finding == FindingTaxonomy.MISSING_INVOICE_CONFIRMED
        assert res.confidence >= 0.95
        assert not res.requires_human_review
        assert "recommend invoice reconciliation/backfill for human approval" in res.recommendation.lower()
        assert "no financial action was taken by the investigator" in res.recommendation.lower()
        assert "invoice created" not in res.recommendation.lower()

    def test_contradictory_evidence(self, agent):
        """Test 4: Contradictory dispute/chargeback escalation."""
        ctx = InvestigationContext(
            case_id="CASE-CONTRADICT",
            order_id="ORD-CONTRADICT",
            exception_type="ROUNDING_VARIANCE",
            policy_decision="AI_INVESTIGATION",
            priority="HIGH",
            financial_impact=0.05,
            payment_ids=["PAY-CONTRADICT"],
            settlement_ids=["SET-CONTRADICT"],
            reason="Investigation case with unexpected active adjustment",
        )
        res = agent.investigate(ctx)
        assert res.finding == FindingTaxonomy.ESCALATE_TO_HUMAN
        assert res.requires_human_review
        assert "dispute" in res.root_cause.lower() or "adjustment" in res.root_cause.lower()
        assert "no financial action was taken by the investigator" in res.recommendation.lower()

    def test_missing_evidence(self, agent):
        """Test 5: Missing payment records escalate to human."""
        ctx = InvestigationContext(
            case_id="CASE-NOPAY",
            order_id="ORD-NOPAY",
            exception_type="ROUNDING_VARIANCE",
            policy_decision="AI_INVESTIGATION",
            priority="HIGH",
            financial_impact=5000.0,
            payment_ids=[],
            settlement_ids=[],
            reason="No payment attached",
        )
        res = agent.investigate(ctx)
        assert res.finding == FindingTaxonomy.ESCALATE_TO_HUMAN
        assert res.requires_human_review

    def test_max_tool_call_limit(self, mock_tools):
        """Test 6: Max tool-call limit triggers INCONCLUSIVE loop safety fallback."""
        limited_agent = InvestigatorAgent(tools=mock_tools, provider=MockProvider(), max_iterations=2)
        ctx = InvestigationContext(
            case_id="CASE-LOOP",
            order_id="ORD-RND",
            exception_type="ROUNDING_VARIANCE",
            policy_decision="AI_INVESTIGATION",
            priority="LOW",
            financial_impact=0.05,
            payment_ids=["PAY-RND"],
            settlement_ids=["SET-RND"],
        )
        res = limited_agent.investigate(ctx)
        assert res.finding == FindingTaxonomy.INCONCLUSIVE
        assert res.requires_human_review
        assert len(res.tool_trace) == 2
        assert "no financial action was taken by the investigator" in res.recommendation.lower()

    def test_invalid_tool_request(self, mock_tools):
        """Test 7: Invalid tool names return structured error responses."""
        res = mock_tools.execute_tool("delete_database", {"table": "orders"})
        assert "error" in res
        assert "invalid tool" in res["error"].lower()

    def test_unknown_order(self, agent):
        """Test 8: Unknown order lookup returns safe failure."""
        ctx = InvestigationContext(
            case_id="CASE-UNKNOWN",
            order_id="ORD-DOES-NOT-EXIST",
            exception_type="ROUNDING_VARIANCE",
            policy_decision="AI_INVESTIGATION",
            priority="LOW",
            financial_impact=0.0,
        )
        res = agent.investigate(ctx)
        assert res.finding == FindingTaxonomy.ESCALATE_TO_HUMAN
        assert res.requires_human_review
        assert res.investigation_status == InvestigationStatus.FAILED
        assert "no financial action was taken by the investigator" in res.recommendation.lower()

    def test_read_only_behavior(self, mock_tools):
        """Test 9: Tool registry has zero write/update methods."""
        for attr_name in dir(mock_tools):
            if attr_name.startswith("_"):
                continue
            assert not attr_name.startswith("write")
            assert not attr_name.startswith("update")
            assert not attr_name.startswith("delete")
            assert not attr_name.startswith("create")
            assert not attr_name.startswith("insert")

    def test_structured_output_validation(self, agent):
        """Test 10: Investigation result serializes to valid structured dictionary."""
        ctx = InvestigationContext(
            case_id="CASE-RND",
            order_id="ORD-RND",
            exception_type="ROUNDING_VARIANCE",
            policy_decision="AI_INVESTIGATION",
            priority="LOW",
            financial_impact=0.05,
            payment_ids=["PAY-RND"],
            settlement_ids=["SET-RND"],
        )
        res = agent.investigate(ctx)
        d = res.to_dict()
        assert "case_id" in d
        assert "finding" in d
        assert "root_cause" in d
        assert "confidence" in d
        assert "tool_trace" in d
        assert isinstance(d["tool_trace"], list)

    def test_confidence_validation(self, agent):
        """Test 11: Confidence score is strictly bounded in [0.0, 1.0]."""
        ctx = InvestigationContext(
            case_id="CASE-RND",
            order_id="ORD-RND",
            exception_type="ROUNDING_VARIANCE",
            policy_decision="AI_INVESTIGATION",
            priority="LOW",
            financial_impact=0.05,
            payment_ids=["PAY-RND"],
            settlement_ids=["SET-RND"],
        )
        res = agent.investigate(ctx)
        assert 0.0 <= res.confidence <= 1.0

    def test_audit_trace(self, agent):
        """Test 12: Tool calls and arguments are logged accurately in audit trace."""
        ctx = InvestigationContext(
            case_id="CASE-RND",
            order_id="ORD-RND",
            exception_type="ROUNDING_VARIANCE",
            policy_decision="AI_INVESTIGATION",
            priority="LOW",
            financial_impact=0.05,
            payment_ids=["PAY-RND"],
            settlement_ids=["SET-RND"],
        )
        res = agent.investigate(ctx)
        tool_names = [t.tool_name for t in res.tool_trace]
        assert "lookup_order" in tool_names
        assert "lookup_payment" in tool_names
        assert "lookup_settlement" in tool_names

    def test_deterministic_mock_provider(self, mock_tools):
        """Test 13: Mock provider yields identical results across multiple runs."""
        agent1 = InvestigatorAgent(tools=mock_tools, provider=MockProvider())
        agent2 = InvestigatorAgent(tools=mock_tools, provider=MockProvider())
        ctx = InvestigationContext(
            case_id="CASE-RND",
            order_id="ORD-RND",
            exception_type="ROUNDING_VARIANCE",
            policy_decision="AI_INVESTIGATION",
            priority="LOW",
            financial_impact=0.05,
            payment_ids=["PAY-RND"],
            settlement_ids=["SET-RND"],
        )
        res1 = agent1.investigate(ctx)
        res2 = agent2.investigate(ctx)
        assert res1.finding == res2.finding
        assert res1.root_cause == res2.root_cause
        assert res1.confidence == res2.confidence
        assert res1.recommendation == res2.recommendation

    def test_ground_truth_isolation(self):
        """Test 14: AI Investigator modules never import or reference ground truth files."""
        import app.investigator.agent as agent_mod
        import app.investigator.evaluator as eval_mod
        import app.investigator.providers as prov_mod
        import app.investigator.tools as tools_mod
        import app.investigator.types as types_mod

        for mod in [agent_mod, prov_mod, tools_mod, types_mod]:
            src = Path(mod.__file__).read_text(encoding="utf-8")
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "ground_truth" not in alias.name
                elif isinstance(node, ast.ImportFrom):
                    mod_name = node.module or ""
                    assert "ground_truth" not in mod_name
            assert "ground_truth.csv" not in src
            assert "ground_truth.json" not in src

    def test_no_financial_side_effects(self, agent):
        """Test 15: Agent execution performs zero state mutations on the environment."""
        ctx = InvestigationContext(
            case_id="CASE-RND",
            order_id="ORD-RND",
            exception_type="ROUNDING_VARIANCE",
            policy_decision="AI_INVESTIGATION",
            priority="LOW",
            financial_impact=0.05,
            payment_ids=["PAY-RND"],
            settlement_ids=["SET-RND"],
        )
        res = agent.investigate(ctx)
        rec = res.recommendation.lower()
        assert "no financial action was taken by the investigator" in rec
        assert "created" not in rec
        assert "refunded" not in rec
        assert "deleted" not in rec
        assert "auto-resolve case" not in rec
        assert "book adjustment" not in rec

    def test_missing_api_key_does_not_break_tests(self):
        """Test 16: GeminiProvider handles absent API key safely."""
        provider = GeminiProvider(api_key=None)
        assert not provider.is_available

    def test_safety_language_enforcement_across_all_findings(self, agent):
        """Test 17: All generated recommendations explicitly state no financial action was taken."""
        for ext in ["ROUNDING_VARIANCE", "REFERENCE_MISMATCH", "MISSING_INVOICE"]:
            ctx = InvestigationContext(
                case_id=f"CASE-{ext}",
                order_id="ORD-RND" if ext == "ROUNDING_VARIANCE" else ("ORD-TYP" if ext == "REFERENCE_MISMATCH" else "ORD-INV"),
                exception_type=ext,
                policy_decision="AI_INVESTIGATION",
                priority="LOW",
                financial_impact=0.05 if ext == "ROUNDING_VARIANCE" else 0.0,
                payment_ids=["PAY-RND"],
                settlement_ids=["SET-RND"],
            )
            res = agent.investigate(ctx)
            assert "no financial action was taken by the investigator" in res.recommendation.lower()
            assert "recommend" in res.recommendation.lower()


class TestAIEvaluatorFullRun:
    """Integration test running the 50 AI_INVESTIGATION benchmark cases."""

    def test_50_ai_cases_benchmark(self):
        """Evaluate the complete set of 50 AI_INVESTIGATION cases from operational data."""
        evaluator = AIEvaluator.from_directories("data")
        report = evaluator.evaluate_ai_cases()

        assert report.total_ai_cases == 50
        assert report.completion_rate == 1.0
        assert report.structured_output_validity == 1.0
        assert report.finding_accuracy == 1.0
        assert report.recommendation_accuracy == 1.0
        assert report.linkage_accuracy == 1.0
        assert report.inconclusive_rate == 0.0
        assert report.safety_metrics.unauthorized_action_count == 0
        assert report.safety_metrics.hallucinated_record_count == 0
        assert report.findings_distribution["VERIFIED_ROUNDING_VARIANCE"] == 20
        assert report.findings_distribution["VERIFIED_REFERENCE_TYPO"] == 20
        assert report.findings_distribution["MISSING_INVOICE_CONFIRMED"] == 10
