"""Integration and unit tests for ReconGuard FastAPI REST API."""

import ast
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)


class TestHealthAPI:
    """Test health check endpoints."""

    def test_health_root(self):
        """Test GET /health returns 200 healthy."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_api_health(self):
        """Test GET /api/health returns 200 healthy."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestDashboardAPI:
    """Test Dashboard Summary API."""

    def test_dashboard_summary_status_and_keys(self):
        """Test GET /api/dashboard/summary returns full KPI structure."""
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 200
        data = response.json()

        expected_keys = [
            "total_cases",
            "auto_resolved",
            "ai_investigation",
            "human_review",
            "escalated",
            "total_financial_exposure",
            "high_priority_cases",
            "medium_priority_cases",
            "low_priority_cases",
            "matched_cases",
            "unmatched_cases",
            "discrepancy_cases",
            "ambiguous_cases",
            "financial_impact_by_decision",
            "financial_impact_by_priority",
            "exception_type_counts",
        ]
        for k in expected_keys:
            assert k in data, f"Key '{k}' missing from dashboard summary"

    def test_dashboard_totals_and_consistency(self):
        """Test that dashboard counts and metrics are derived and balance correctly."""
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 200
        data = response.json()

        assert data["total_cases"] == 1000
        # Decision sum
        decision_sum = (
            data["auto_resolved"]
            + data["ai_investigation"]
            + data["human_review"]
            + data["escalated"]
        )
        assert decision_sum == 1000

        # Priority sum
        priority_sum = (
            data["high_priority_cases"]
            + data["medium_priority_cases"]
            + data["low_priority_cases"]
        )
        assert priority_sum == 1000

        # Match status sum
        match_sum = (
            data["matched_cases"]
            + data["unmatched_cases"]
            + data["discrepancy_cases"]
            + data["ambiguous_cases"]
        )
        assert match_sum == 1000

        # Financial exposure
        assert data["total_financial_exposure"] > 0.0
        assert isinstance(data["financial_impact_by_decision"], dict)
        assert isinstance(data["financial_impact_by_priority"], dict)

    def test_dashboard_benchmark_metrics(self):
        """Test GET /api/dashboard/benchmark returns verified Phase 1 metrics."""
        response = client.get("/api/dashboard/benchmark")
        assert response.status_code == 200
        data = response.json()

        assert data["total_records"] == 1000
        assert data["deterministic_coverage"] == 0.82
        assert data["deterministic_correctness"] == 0.9512
        assert data["classification_accuracy"] == 0.939
        assert data["binary_exception_f1"] == 1.0
        assert data["payment_linkage_f1"] == 1.0
        assert data["settlement_linkage_f1"] == 0.9484
        assert data["total_exposure_identified"] == 1109091.50
        assert data["deterministic_throughput_rps"] > 500


class TestCasesAPI:
    """Test Cases list, filtering, pagination, and detail endpoints."""

    def test_cases_pagination(self):
        """Test pagination parameters and page size boundaries."""
        res_p1 = client.get("/api/cases?page=1&page_size=10")
        assert res_p1.status_code == 200
        d1 = res_p1.json()
        assert d1["total"] == 1000
        assert d1["page"] == 1
        assert d1["page_size"] == 10
        assert d1["total_pages"] == 100
        assert len(d1["cases"]) == 10

        res_p2 = client.get("/api/cases?page=2&page_size=10")
        assert res_p2.status_code == 200
        d2 = res_p2.json()
        assert len(d2["cases"]) == 10
        # Assert page 1 and page 2 items are distinct
        p1_ids = [c["case_id"] for c in d1["cases"]]
        p2_ids = [c["case_id"] for c in d2["cases"]]
        assert set(p1_ids).isdisjoint(set(p2_ids))

    def test_cases_deterministic_ordering(self):
        """Test cases are returned in deterministic order."""
        res = client.get("/api/cases?page=1&page_size=20")
        assert res.status_code == 200
        cases = res.json()["cases"]
        case_ids = [c["case_id"] for c in cases]
        assert case_ids == sorted(case_ids)

    def test_cases_filter_decision(self):
        """Test filtering cases by policy decision."""
        res = client.get("/api/cases?decision=AI_INVESTIGATION")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 50
        for c in data["cases"]:
            assert c["decision"] == "AI_INVESTIGATION"

    def test_cases_filter_priority(self):
        """Test filtering cases by priority."""
        res_high = client.get("/api/cases?priority=HIGH")
        assert res_high.status_code == 200
        data_high = res_high.json()
        assert data_high["total"] == 170
        for c in data_high["cases"]:
            assert c["priority"] == "HIGH"

        res_med = client.get("/api/cases?priority=MEDIUM")
        assert res_med.status_code == 200
        assert res_med.json()["total"] == 30

        res_low = client.get("/api/cases?priority=LOW")
        assert res_low.status_code == 200
        assert res_low.json()["total"] == 800

    def test_cases_filter_exception_type(self):
        """Test filtering cases by exception category."""
        res = client.get("/api/cases?exception_type=ROUNDING_VARIANCE")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 20
        for c in data["cases"]:
            assert c["exception_type"] == "ROUNDING_VARIANCE"

    def test_cases_search_case_id_and_order_id(self):
        """Test searching cases by case_id or order_id substring."""
        res_case = client.get("/api/cases?search=CASE-000921")
        assert res_case.status_code == 200
        assert res_case.json()["total"] >= 1
        assert res_case.json()["cases"][0]["case_id"] == "CASE-000921"

        res_order = client.get("/api/cases?search=ORD-000921")
        assert res_order.status_code == 200
        assert res_order.json()["total"] >= 1
        assert res_order.json()["cases"][0]["order_id"] == "ORD-000921"

    def test_cases_invalid_filter_parameter(self):
        """Test invalid decision or priority returns HTTP 400."""
        res_bad_dec = client.get("/api/cases?decision=INVALID_DECISION")
        assert res_bad_dec.status_code == 400

        res_bad_prio = client.get("/api/cases?priority=INVALID_PRIORITY")
        assert res_bad_prio.status_code == 400

    def test_case_detail_found(self):
        """Test GET /api/cases/{case_id} returns complete transaction chain."""
        res = client.get("/api/cases/CASE-000921")
        assert res.status_code == 200
        data = res.json()
        assert data["case_id"] == "CASE-000921"
        assert data["order_id"] == "ORD-000921"
        assert data["decision"] == "AI_INVESTIGATION"
        assert data["exception_type"] == "REFERENCE_MISMATCH"
        assert "transaction_chain" in data
        tx = data["transaction_chain"]
        assert tx["order"] is not None
        assert tx["order"]["order_id"] == "ORD-000921"
        assert len(tx["payments"]) >= 1
        assert len(tx["settlements"]) >= 1

    def test_case_detail_not_found(self):
        """Test GET /api/cases/{case_id} returns HTTP 404 for unknown case."""
        res = client.get("/api/cases/CASE-NONEXISTENT")
        assert res.status_code == 404

    def test_case_evidence_found(self):
        """Test GET /api/cases/{case_id}/evidence returns deterministic match evidence."""
        res = client.get("/api/cases/CASE-000921/evidence")
        assert res.status_code == 200
        data = res.json()
        assert data["case_id"] == "CASE-000921"
        assert data["order_id"] == "ORD-000921"
        assert data["match_method"] == "FUZZY"
        assert data["match_confidence"] > 0.0
        assert isinstance(data["evidence"], dict)

    def test_case_evidence_not_found(self):
        """Test GET /api/cases/{case_id}/evidence returns 404 for unknown case."""
        res = client.get("/api/cases/CASE-UNKNOWN/evidence")
        assert res.status_code == 404


class TestInvestigationsAPI:
    """Test AI Investigation listing, retrieval, and trigger endpoints."""

    def test_list_investigations(self):
        """Test GET /api/investigations returns list."""
        res = client.get("/api/investigations")
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "investigations" in data
        assert isinstance(data["investigations"], list)

    def test_trigger_investigation_on_eligible_case(self):
        """Test POST /api/cases/{case_id}/investigate on AI_INVESTIGATION case."""
        res = client.post("/api/cases/CASE-000901/investigate", json={"provider": "mock"})
        assert res.status_code == 200
        data = res.json()
        assert data["case_id"] == "CASE-000901"
        assert data["finding"] == "VERIFIED_ROUNDING_VARIANCE"
        assert data["confidence"] >= 0.95
        assert not data["requires_human_review"]
        assert "no financial action was taken by the investigator" in data["recommendation"].lower()
        assert len(data["tool_trace"]) >= 4

    def test_get_investigation_detail_after_run(self):
        """Test GET /api/investigations/{case_id} returns previously executed investigation."""
        client.post("/api/cases/CASE-000901/investigate", json={"provider": "mock"})
        res = client.get("/api/investigations/CASE-000901")
        assert res.status_code == 200
        data = res.json()
        assert data["case_id"] == "CASE-000901"
        assert data["finding"] == "VERIFIED_ROUNDING_VARIANCE"

    def test_get_investigation_detail_not_found(self):
        """Test GET /api/investigations/{case_id} returns 404 if not found."""
        res = client.get("/api/investigations/CASE-UNINVESTIGATED")
        assert res.status_code == 404

    def test_trigger_investigation_on_ineligible_case(self):
        """Test POST /api/cases/{case_id}/investigate on AUTO_RESOLVE case returns 400."""
        res = client.post("/api/cases/CASE-000001/investigate", json={"provider": "mock"})
        assert res.status_code == 400
        assert "only cases with decision 'ai_investigation'" in res.json()["detail"].lower()

    def test_trigger_investigation_on_nonexistent_case(self):
        """Test POST /api/cases/{case_id}/investigate on unknown case returns 404."""
        res = client.post("/api/cases/CASE-999999/investigate", json={"provider": "mock"})
        assert res.status_code == 404


class TestAPISafetyAndIsolation:
    """Test safety, read-only guarantees, and ground-truth isolation."""

    def test_api_ground_truth_isolation(self):
        """Test that API routes and schemas never import ground truth."""
        api_files = list(Path("app/api").glob("**/*.py")) + [Path("app/services/reconciliation_service.py")]
        for f in api_files:
            src = f.read_text(encoding="utf-8")
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "ground_truth" not in alias.name, f"Ground truth import found in {f}"
                elif isinstance(node, ast.ImportFrom):
                    mod_name = node.module or ""
                    assert "ground_truth" not in mod_name, f"Ground truth import found in {f}"
            assert "ground_truth.csv" not in src
            assert "ground_truth.json" not in src

    def test_no_financial_write_routes(self):
        """Test that only safe GET/POST routes exist and no write/mutation endpoints exist."""
        for route in app.routes:
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", set())
            if path.startswith("/api/"):
                assert "DELETE" not in methods, f"Unsafe DELETE method on {path}"
                assert "PUT" not in methods, f"Unsafe PUT method on {path}"
                assert "PATCH" not in methods, f"Unsafe PATCH method on {path}"
                if "POST" in methods:
                    assert path.endswith("/investigate"), f"Unsafe POST endpoint on {path}"
