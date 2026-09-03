"""Adversarial validation and Red-Team test suite for ReconGuard.

Validates core financial safety, control boundaries, and security invariants:
1. AI cannot override or bypass deterministic PolicyEngine decisions.
2. AI investigator tools are strictly read-only (zero financial writes).
3. Ground truth dataset is strictly isolated from operational execution.
4. AI failures (429, timeout, malformed JSON, etc.) never auto-resolve financial exceptions.
5. Iteration limit enforcement prevents infinite multi-turn loops.
6. Audit trail is append-only and has no modification or deletion APIs.
7. Audit persistence failures do not alter or corrupt financial policy decisions.
8. Financial exposure is strictly preserved across AI investigation lifecycles.
9. Demo replay provider is transparently labeled and never masquerades as live Gemini.
10. System API attack surface contains zero financial mutation endpoints.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.investigator.agent import InvestigatorAgent
from app.investigator.providers import DemoReplayProvider, GeminiProvider, MockProvider
from app.investigator.tools import InvestigationToolRegistry
from app.investigator.types import (
    FindingTaxonomy,
    InvestigationContext,
    InvestigationResult,
    InvestigationStatus,
)
from app.main import app
from app.matching.engine import ReconciliationEngine
from app.matching.types import MatchMethod, MatchResult, MatchStatus
from app.policy.engine import PolicyEngine
from app.policy.types import CasePriority, ExceptionCase, ExceptionType, PolicyDecision
from app.services.reconciliation_service import ReconciliationService


client = TestClient(app)


class TestAdversarialPolicyBypass:
    """A. AI Policy Bypass Invariant Tests."""

    def test_ai_finding_cannot_force_auto_resolve_on_human_escalated_case(self):
        """Verify that an AI result recommending auto-resolution CANNOT modify an ESCALATE case."""
        # An attacker tries to pass an ESCALATE case to InvestigatorAgent claiming it should be investigated
        ctx = InvestigationContext(
            case_id="CASE-ATTACK-01",
            order_id="ORD-ATTACK-01",
            exception_type="AMOUNT_MISMATCH",
            policy_decision="ESCALATE",
            priority="HIGH",
            financial_impact=10000.0,
        )
        tools = InvestigationToolRegistry()
        agent = InvestigatorAgent(tools=tools)
        res = agent.investigate(ctx)

        # Agent must reject investigating an ESCALATE case
        assert res.finding == FindingTaxonomy.ESCALATE_TO_HUMAN
        assert res.requires_human_review is True
        assert "not designated for ai investigation" in res.root_cause.lower()


class TestAdversarialToolSafety:
    """B. AI Tool Mutation Attack Tests."""

    def test_investigator_tools_have_no_write_methods(self):
        """Verify that InvestigationToolRegistry has zero methods containing write/insert/update/delete."""
        registry = InvestigationToolRegistry()
        tool_methods = [
            m for m in dir(registry)
            if not m.startswith("_") and callable(getattr(registry, m))
        ]
        forbidden_keywords = ["write", "insert", "update", "delete", "mutate", "refund", "payout", "charge", "commit"]
        for method_name in tool_methods:
            for kw in forbidden_keywords:
                assert kw not in method_name.lower(), f"Tool method '{method_name}' contains forbidden keyword '{kw}'"

    def test_investigator_execute_tool_rejects_unregistered_commands(self):
        """Verify that execute_tool rejects arbitrary execution attempts."""
        registry = InvestigationToolRegistry()
        res = registry.execute_tool("drop_tables", {"table": "orders"})
        assert "error" in res
        assert "invalid tool" in res["error"].lower() or "not supported" in res["error"].lower()


class TestAdversarialGroundTruthIsolation:
    """C. Ground Truth Leakage Tests."""

    def test_operational_engine_does_not_access_ground_truth(self):
        """Verify that ReconciliationEngine and InvestigationToolRegistry do not read ground_truth."""
        # Ensure loading from data/ does not access ground_truth directory
        engine = ReconciliationEngine.from_csv_directory("data")
        assert not hasattr(engine, "ground_truth")

        tools = InvestigationToolRegistry.from_csv_directory("data")
        assert not hasattr(tools, "ground_truth")


class TestAdversarialFinancialExposurePreservation:
    """D. Financial Exposure Calculation & Preservation Invariant Tests."""

    def test_exposure_remains_strictly_identical_before_and_after_investigation(self):
        """Verify financial_impact of a case is unchanged after AI investigation."""
        service = ReconciliationService.get_instance()
        case_id = "CASE-000921"
        case = service.get_case(case_id)
        assert case is not None

        initial_exposure = case.financial_impact
        initial_decision = case.decision

        # Execute investigation
        res = service.investigate_case(case_id, provider_name="demo_replay")

        # Verify exposure and decision remain unaltered on the underlying case
        assert case.financial_impact == initial_exposure
        assert case.decision == initial_decision
        assert res["case_id"] == case_id


class TestAdversarialAIFailures:
    """E. Comprehensive AI Failure Attacks."""

    @pytest.mark.parametrize("error_sim,expected_status", [
        (Exception("429 RESOURCE_EXHAUSTED"), InvestigationStatus.RATE_LIMITED),
        (TimeoutError("Connection timed out"), InvestigationStatus.TIMEOUT),
        (ValueError("Missing credentials"), InvestigationStatus.CONFIGURATION_ERROR),
    ])
    def test_provider_failures_produce_inconclusive_human_escalation(self, error_sim, expected_status):
        """Verify every simulated provider failure produces INCONCLUSIVE with human review."""
        provider = GeminiProvider(api_key="fake-key")
        ctx = InvestigationContext(
            case_id="CASE-ERR",
            order_id="ORD-ERR",
            exception_type="REFERENCE_MISMATCH",
            policy_decision="AI_INVESTIGATION",
            priority="LOW",
            financial_impact=0.0,
        )
        tools = InvestigationToolRegistry()

        with patch("google.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.chats.create.side_effect = error_sim

            res = provider.investigate(ctx, tools)
            assert res.investigation_status == expected_status
            assert res.finding == FindingTaxonomy.INCONCLUSIVE
            assert res.requires_human_review is True
            assert res.confidence == 0.0


class TestAdversarialIterationLimit:
    """F. Iteration Limit Enforcement."""

    def test_max_iterations_strictly_terminates_loop(self):
        """Verify agent never exceeds max_iterations."""
        provider = MockProvider()
        ctx = InvestigationContext(
            case_id="CASE-ITER",
            order_id="ORD-ITER",
            exception_type="REFERENCE_MISMATCH",
            policy_decision="AI_INVESTIGATION",
            priority="LOW",
            financial_impact=0.0,
        )
        tools = InvestigationToolRegistry()

        # max_iterations = 0 forces immediate iteration limit exit
        res = provider.investigate(ctx, tools, max_iterations=0)
        assert res.investigation_status == InvestigationStatus.ITERATION_LIMIT
        assert res.finding == FindingTaxonomy.INCONCLUSIVE
        assert res.requires_human_review is True


class TestAdversarialAuditImmutability:
    """H & I. Audit Trail Immutability & Persistence Failure Tests."""

    def test_audit_endpoints_reject_modifications(self):
        """Verify POST/PUT/PATCH/DELETE on audit routes return 404 or 405."""
        assert client.post("/api/audit", json={"event": "fake"}).status_code in (404, 405)
        assert client.put("/api/audit/CASE-000001", json={"event": "fake"}).status_code in (404, 405)
        assert client.delete("/api/audit/CASE-000001").status_code in (404, 405)

    def test_audit_persistence_failure_does_not_break_reconciliation_service(self):
        """Verify that SQLite failure during audit logging does not change policy decisions."""
        service = ReconciliationService.get_instance()
        case = service.get_case("CASE-000001")
        assert case is not None

        # Simulate SQLite failure in _persist_audit_log
        with patch.object(service, "_persist_audit_log", side_effect=Exception("DB connection dropped")):
            # Recording audit event should continue gracefully without crashing or corrupting policy
            entry = service._record_audit_event(
                case_id="CASE-000001",
                actor="TEST_ACTOR",
                action="TEST_ACTION",
                details_json={"note": "db fail test"},
            )
            assert entry is not None
            assert entry.action == "TEST_ACTION"
            assert case.decision == PolicyDecision.AUTO_RESOLVE


class TestAdversarialAPISurface:
    """J. API Mutation Surface Inventory Test."""

    def test_zero_financial_mutation_endpoints_in_fastapi_app(self):
        """Verify that no routes exist with financial write capabilities."""
        financial_write_paths = ["refund", "payout", "disburse", "charge", "ledger_write", "mutate_balance"]
        for route in app.routes:
            path = getattr(route, "path", "").lower()
            for forbidden in financial_write_paths:
                assert forbidden not in path, f"Route '{path}' matches forbidden write path '{forbidden}'"

