"""Tests for ReconGuard Audit Trail & Financial Control Evidence layer."""

from datetime import datetime, timezone
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.models.audit_log import AuditLog
from app.policy.types import PolicyDecision
from app.services.reconciliation_service import ReconciliationService


@pytest.fixture
def client():
    """TestClient for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def service():
    """ReconciliationService instance."""
    return ReconciliationService.get_instance()


def test_audit_log_model_structure():
    """1. Verify AuditLog model attributes, to_dict serialization, and source inference."""
    log = AuditLog(
        audit_id="AUD-CASE-000001-001",
        case_id="CASE-000001",
        actor="RECONCILIATION_ENGINE",
        action="RECONCILIATION_COMPLETED",
        details_json={"source": "DETERMINISTIC", "status": "MATCHED", "financial_impact": 0.0},
        timestamp=datetime.now(timezone.utc),
    )

    assert log.audit_id == "AUD-CASE-000001-001"
    assert log.case_id == "CASE-000001"
    assert log.actor == "RECONCILIATION_ENGINE"
    assert log.action == "RECONCILIATION_COMPLETED"
    assert log.source == "DETERMINISTIC"

    d = log.to_dict()
    assert d["audit_id"] == "AUD-CASE-000001-001"
    assert d["source"] == "DETERMINISTIC"
    assert d["details_json"]["status"] == "MATCHED"


def test_reconciliation_audit_event_created(service):
    """2. Verify reconciliation event is generated for all cases with deterministic source."""
    trail = service.get_audit_trail("CASE-000001")
    assert trail is not None
    events = trail["events"]
    assert len(events) >= 2

    recon_event = events[0]
    assert recon_event["action"] == "RECONCILIATION_COMPLETED"
    assert recon_event["actor"] == "RECONCILIATION_ENGINE"
    assert recon_event["source"] == "DETERMINISTIC"
    assert "status" in recon_event["details_json"]
    assert "order_id" in recon_event["details_json"]


def test_policy_audit_event_created(service):
    """3. Verify policy decision event is generated with decision, priority, and financial impact."""
    trail = service.get_audit_trail("CASE-000001")
    assert trail is not None
    events = trail["events"]

    policy_event = events[1]
    assert policy_event["action"] == "POLICY_DECISION"
    assert policy_event["actor"] == "POLICY_ENGINE"
    assert policy_event["source"] == "DETERMINISTIC"
    assert policy_event["details_json"]["decision"] == "AUTO_RESOLVE"
    assert "financial_impact" in policy_event["details_json"]


def test_ai_investigation_audit_event_flow(service):
    """4. Verify AI investigation creates STARTED and COMPLETED audit events."""
    case_id = "CASE-000921"  # REFERENCE_MISMATCH -> AI_INVESTIGATION
    trail_before = service.get_audit_trail(case_id)
    initial_count = trail_before["total_events"]

    # Trigger investigation via mock provider
    service.investigate_case(case_id, provider_name="mock")

    trail_after = service.get_audit_trail(case_id)
    assert trail_after["total_events"] >= initial_count + 2

    actions = [e["action"] for e in trail_after["events"]]
    assert "AI_INVESTIGATION_STARTED" in actions
    assert "AI_INVESTIGATION_COMPLETED" in actions

    completed_event = next(e for e in trail_after["events"] if e["action"] == "AI_INVESTIGATION_COMPLETED")
    assert completed_event["source"] == "AI"
    assert "finding" in completed_event["details_json"]
    assert "confidence" in completed_event["details_json"]
    assert "tools_called" in completed_event["details_json"]


def test_ai_failure_inconclusive_event(service):
    """5. Verify that an inconclusive or failing AI investigation records failure and escalates."""
    case_id = "CASE-000922"  # AI-eligible case

    # Mock agent that returns inconclusive / incomplete status
    mock_result = MagicMock()
    mock_result.investigation_status.value = "INCONCLUSIVE"
    mock_result.finding.value = "INSUFFICIENT_EVIDENCE"
    mock_result.confidence = 0.2
    mock_result.root_cause = "Rate limit / quota exceeded"
    mock_result.tool_trace = []
    mock_result.provider_used = "mock"
    mock_result.to_dict.return_value = {"status": "INCONCLUSIVE"}

    with patch("app.services.reconciliation_service.InvestigatorAgent") as MockAgentClass:
        mock_agent_inst = MagicMock()
        mock_agent_inst.investigate_case.return_value = mock_result
        MockAgentClass.return_value = mock_agent_inst

        service.investigate_case(case_id, provider_name="mock")

    trail = service.get_audit_trail(case_id)
    actions = [e["action"] for e in trail["events"]]
    assert "AI_INVESTIGATION_FAILED" in actions
    assert "HUMAN_REVIEW_REQUIRED" in actions


def test_human_review_and_escalation_events(service):
    """6. Verify HUMAN_REVIEW and ESCALATE cases have HUMAN_REVIEW_REQUIRED audit events."""
    # CASE-000853 is a CHARGEBACK -> ESCALATE case
    trail_esc = service.get_audit_trail("CASE-000853")
    assert trail_esc is not None
    actions_esc = [e["action"] for e in trail_esc["events"]]
    assert "HUMAN_REVIEW_REQUIRED" in actions_esc

    esc_event = next(e for e in trail_esc["events"] if e["action"] == "HUMAN_REVIEW_REQUIRED")
    assert esc_event["source"] == "HUMAN"
    assert esc_event["details_json"]["decision"] == "ESCALATE"
    assert esc_event["details_json"]["required_desk"] == "DISPUTE_DESK"


def test_audit_event_chronological_ordering(service):
    """7. Verify all events in a case audit trail are strictly ordered chronologically."""
    case_id = "CASE-000921"
    service.investigate_case(case_id, provider_name="mock")
    trail = service.get_audit_trail(case_id)

    events = trail["events"]
    assert len(events) >= 4
    # Event 1: RECONCILIATION_COMPLETED
    assert events[0]["action"] == "RECONCILIATION_COMPLETED"
    # Event 2: POLICY_DECISION
    assert events[1]["action"] == "POLICY_DECISION"
    # Event 3: AI_INVESTIGATION_STARTED
    assert events[2]["action"] == "AI_INVESTIGATION_STARTED"
    # Event 4: AI_INVESTIGATION_COMPLETED
    assert events[3]["action"] == "AI_INVESTIGATION_COMPLETED"


def test_case_audit_filtering_and_isolation(service):
    """8. Verify that audit events for case A do not bleed into case B."""
    trail_a = service.get_audit_trail("CASE-000001")
    trail_b = service.get_audit_trail("CASE-000002")

    for e in trail_a["events"]:
        assert e["case_id"] == "CASE-000001"

    for e in trail_b["events"]:
        assert e["case_id"] == "CASE-000002"


def test_audit_api_endpoint_response(client):
    """9. Verify GET /api/audit/{case_id} returns valid schema with 200 OK."""
    resp = client.get("/api/audit/CASE-000001")
    assert resp.status_code == 200
    data = resp.json()

    assert data["case_id"] == "CASE-000001"
    assert data["order_id"] == "ORD-000001"
    assert data["total_events"] >= 2
    assert isinstance(data["events"], list)
    assert data["events"][0]["action"] == "RECONCILIATION_COMPLETED"

    # 404 for nonexistent case
    resp_404 = client.get("/api/audit/NONEXISTENT-999")
    assert resp_404.status_code == 404


def test_audit_api_is_read_only(client):
    """10. Verify that POST/PUT/DELETE methods are rejected on the audit endpoints."""
    resp_post = client.post("/api/audit/CASE-000001", json={"action": "HACK"})
    assert resp_post.status_code in (404, 405)

    resp_put = client.put("/api/audit/CASE-000001", json={"action": "HACK"})
    assert resp_put.status_code in (404, 405)

    resp_delete = client.delete("/api/audit/CASE-000001")
    assert resp_delete.status_code in (404, 405)


def test_secret_and_prompt_protection(service):
    """11. Verify no API keys, secrets, full prompts, or system instructions are saved in audit logs."""
    case_id = "CASE-000921"
    service.investigate_case(case_id, provider_name="mock")
    trail = service.get_audit_trail(case_id)

    trail_str = json.dumps(trail)
    assert "AIza" not in trail_str
    assert "GEMINI_API_KEY" not in trail_str
    assert "sk-" not in trail_str
    assert "system_instruction" not in trail_str
    assert "chain_of_thought" not in trail_str


def test_audit_persistence_failure_does_not_break_policy(service):
    """12. Verify that if DB persistence raises an exception, policy decisions and service operations still succeed."""
    with patch("app.database.SessionLocal", side_effect=Exception("Database connection failed")):
        # investigate_case should still complete successfully in-memory
        result = service.investigate_case("CASE-000923", provider_name="mock")
        assert result is not None
        assert result["finding"] is not None

        trail = service.get_audit_trail("CASE-000923")
        assert trail is not None
        assert trail["total_events"] >= 4

