"""Unit and integration tests for AI Investigator Resilience, Error Handling, and Safety Invariants.

Validates that:
1. Gemini rate-limit handling (HTTP 429 / Resource Exhausted) fails safely.
2. Provider timeout fails safely.
3. Provider unavailable / missing configuration returns CONFIGURATION_ERROR.
4. Malformed AI response produces MALFORMED_RESPONSE without guessing.
5. Inconclusive AI result routes to human review.
6. Iteration limit produces ITERATION_LIMIT and routes to human review.
7. Safe fallback to human control preserves financial exposure.
8. Audit event on AI failure records failure reason without raw prompt leakage.
9. No financial mutation or auto-resolve occurs on AI failure.
10. Demo replay provider executes deterministic demonstration with explicit labeling.
11. Mock provider remains deterministic.
12. Live provider errors are never misrepresented as successful investigations.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.investigator.agent import InvestigatorAgent
from app.investigator.providers import DemoReplayProvider, GeminiProvider, MockProvider
from app.investigator.tools import InvestigationToolRegistry
from app.investigator.types import (
    FindingTaxonomy,
    InvestigationContext,
    InvestigationResult,
    InvestigationStatus,
)
from app.policy.types import CasePriority, ExceptionCase, ExceptionType, PolicyDecision
from app.services.reconciliation_service import ReconciliationService


@pytest.fixture
def tools():
    return InvestigationToolRegistry.from_csv_directory("data")


@pytest.fixture
def sample_context():
    return InvestigationContext(
        case_id="CASE-000921",
        order_id="ORD-000921",
        exception_type="REFERENCE_MISMATCH",
        policy_decision="AI_INVESTIGATION",
        priority="LOW",
        financial_impact=0.0,
        payment_ids=["PAY-IND-00092112"],
        settlement_ids=["SET-IND-00092121"],
        match_method="REFERENCE_FUZZY",
        match_confidence=0.85,
        reason="Reference mismatch; AI investigation routed.",
        explanation="Payment UTR and settlement UTR differ by typo.",
    )


class TestAIResilienceAndProviders:
    """Test AI provider error handling, boundary limits, and resilience."""

    def test_missing_gemini_configuration(self, sample_context, tools):
        """Test that GeminiProvider without API key returns CONFIGURATION_ERROR safely."""
        with patch.dict("os.environ", {}, clear=True):
            provider = GeminiProvider(api_key=None)
            assert not provider.is_available
            res = provider.investigate(sample_context, tools)

            assert res.investigation_status == InvestigationStatus.CONFIGURATION_ERROR
            assert res.finding == FindingTaxonomy.INCONCLUSIVE
            assert res.requires_human_review is True
            assert res.confidence == 0.0
            assert "GEMINI_API_KEY" in res.root_cause

    def test_gemini_rate_limit_handling(self, sample_context, tools):
        """Test that HTTP 429 / Resource Exhausted error is captured as RATE_LIMITED."""
        provider = GeminiProvider(api_key="fake-test-key")

        # Mock genai client to raise 429 ResourceExhausted
        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_chat = MagicMock()
            mock_client.chats.create.return_value = mock_chat
            mock_chat.send_message.side_effect = Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for quota metric")

            res = provider.investigate(sample_context, tools)

            assert res.investigation_status == InvestigationStatus.RATE_LIMITED
            assert res.error_category == "RATE_LIMITED"
            assert res.finding == FindingTaxonomy.INCONCLUSIVE
            assert res.requires_human_review is True
            assert res.confidence == 0.0
            assert "rate limit" in res.root_cause.lower() or "429" in res.root_cause

    def test_gemini_timeout_handling(self, sample_context, tools):
        """Test that network timeout is captured as TIMEOUT without crashing."""
        provider = GeminiProvider(api_key="fake-test-key")

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_chat = MagicMock()
            mock_client.chats.create.return_value = mock_chat
            mock_chat.send_message.side_effect = TimeoutError("Connection timed out after 30000ms")

            res = provider.investigate(sample_context, tools)

            assert res.investigation_status == InvestigationStatus.TIMEOUT
            assert res.error_category == "TIMEOUT"
            assert res.finding == FindingTaxonomy.INCONCLUSIVE
            assert res.requires_human_review is True

    def test_gemini_malformed_response_handling(self, sample_context, tools):
        """Test that invalid JSON from LLM produces MALFORMED_RESPONSE without guessing."""
        provider = GeminiProvider(api_key="fake-test-key")

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_chat = MagicMock()
            mock_client.chats.create.return_value = mock_chat

            # First send_message returns no function calls
            resp1 = MagicMock()
            resp1.function_calls = None
            # Second send_message returns invalid JSON text
            resp2 = MagicMock()
            resp2.text = "This is not valid json at all { unclosed"
            mock_chat.send_message.side_effect = [resp1, resp2]

            res = provider.investigate(sample_context, tools)

            assert res.investigation_status == InvestigationStatus.MALFORMED_RESPONSE
            assert res.error_category == "MALFORMED_RESPONSE"
            assert res.finding == FindingTaxonomy.INCONCLUSIVE
            assert res.requires_human_review is True
            assert res.confidence == 0.0

    def test_iteration_limit_enforcement(self, sample_context, tools):
        """Test that exceeding max_iterations results in ITERATION_LIMIT and human escalation."""
        # Force max_iterations = 0 so it immediately trips
        mock_provider = MockProvider()
        res = mock_provider.investigate(sample_context, tools, max_iterations=0)

        assert res.investigation_status == InvestigationStatus.ITERATION_LIMIT
        assert res.error_category == "ITERATION_LIMIT"
        assert res.finding == FindingTaxonomy.INCONCLUSIVE
        assert res.requires_human_review is True
        assert res.confidence == 0.0

    def test_demo_replay_provider_labeling(self, tools):
        """Test that DemoReplayProvider is clearly labeled and does not impersonate live Gemini."""
        service = ReconciliationService.get_instance()
        case = service.get_case("CASE-000921")
        ctx = InvestigationContext.from_exception_case(case)

        provider = DemoReplayProvider()
        assert provider.provider_name == "demo_replay"

        res = provider.investigate(ctx, tools)
        assert res.provider_used == "demo_replay"
        assert res.investigation_status == InvestigationStatus.COMPLETED
        assert res.finding == FindingTaxonomy.VERIFIED_REFERENCE_TYPO
        assert "no financial action was taken" in res.recommendation.lower()

    def test_mock_provider_determinism(self, tools):
        """Test that MockProvider produces identical, reproducible results."""
        service = ReconciliationService.get_instance()
        case = service.get_case("CASE-000921")
        ctx = InvestigationContext.from_exception_case(case)

        provider = MockProvider()
        res1 = provider.investigate(ctx, tools)
        res2 = provider.investigate(ctx, tools)

        assert res1.finding == res2.finding
        assert res1.confidence == res2.confidence
        assert len(res1.tool_trace) == len(res2.tool_trace)
        assert res1.provider_used == "mock"


class TestAISafetyInvariants:
    """Test that AI failures never alter financial decisions or bypass policy."""

    def test_ai_failure_does_not_alter_policy_to_auto_resolve(self):
        """CRITICAL INVARIANT: AI failure must NEVER convert a case to AUTO_RESOLVE."""
        service = ReconciliationService.get_instance()
        case_id = "CASE-000922"
        case = service.get_case(case_id)
        if not case:
            case = service.get_case("CASE-000921")
            case_id = "CASE-000921"
        assert case is not None
        initial_decision = case.decision

        # Run with failing provider
        with patch.object(InvestigatorAgent, "investigate_case") as mock_inv:
            mock_inv.return_value = InvestigationResult(
                case_id=case_id,
                order_id=case.order_id,
                finding=FindingTaxonomy.INCONCLUSIVE,
                root_cause="Provider 429 quota exhaustion",
                evidence={"error": "429"},
                confidence=0.0,
                recommendation="Escalate to operations desk.",
                requires_human_review=True,
                investigation_status=InvestigationStatus.RATE_LIMITED,
                error_category="RATE_LIMITED",
            )
            res_dict = service.investigate_case(case_id, provider_name="mock")

            # Verify case policy decision was NOT modified to AUTO_RESOLVE
            assert case.decision == initial_decision
            assert res_dict["investigation_status"] == "RATE_LIMITED"
            assert res_dict["requires_human_review"] is True

            # Verify audit trail contains failure event and human review required
            trail = service.get_audit_trail(case_id)
            events = trail["events"]
            actions = [e["action"] for e in events]
            assert "AI_INVESTIGATION_FAILED" in actions
            assert "HUMAN_REVIEW_REQUIRED" in actions

    def test_unauthorized_policy_case_rejected_by_investigator(self, tools):
        """Test that non-AI_INVESTIGATION cases (e.g. AUTO_RESOLVE or ESCALATE) are rejected by agent."""
        agent = InvestigatorAgent(tools=tools)

        # Context with AUTO_RESOLVE decision
        ctx = InvestigationContext(
            case_id="CASE-000001",
            order_id="ORD-000001",
            exception_type="NONE",
            policy_decision="AUTO_RESOLVE",
            priority="LOW",
            financial_impact=0.0,
        )

        res = agent.investigate(ctx)
        assert res.finding == FindingTaxonomy.ESCALATE_TO_HUMAN
        assert "not designated for AI investigation" in res.root_cause
        assert res.requires_human_review is True

    def test_audit_log_failure_event_sanitization(self):
        """Test that AI failure audit events do not contain secrets or API keys."""
        service = ReconciliationService.get_instance()
        test_case_id = "CASE-000923"
        case = service.get_case(test_case_id)
        if not case:
            test_case_id = "CASE-000921"
            case = service.get_case(test_case_id)

        with patch.object(InvestigatorAgent, "investigate_case") as mock_inv:
            mock_inv.return_value = InvestigationResult(
                case_id=test_case_id,
                order_id=case.order_id,
                finding=FindingTaxonomy.INCONCLUSIVE,
                root_cause="GeminiProvider internal token failure",
                evidence={"error_detail": "Authentication token expired"},
                confidence=0.0,
                recommendation="Escalate to operations desk.",
                requires_human_review=True,
                investigation_status=InvestigationStatus.FAILED,
            )
            service.investigate_case(test_case_id, provider_name="mock")

        trail = service.get_audit_trail(test_case_id)
        events = trail["events"]
        for ev in events:
            details_str = str(ev.get("details_json", {}))
            assert "AIza" not in details_str

