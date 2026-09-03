"""Tests for the ReconGuard Benchmark & Financial Exposure Evaluation layer."""

import json
from pathlib import Path
import tempfile

import pytest

from evaluation.run_benchmark import generate_markdown_report, run_full_benchmark


def test_run_full_benchmark_mock():
    """Verify that the full benchmark runs cleanly against the 1,000-case dataset."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        json_out = Path(tmp_dir) / "test_results.json"
        md_out = Path(tmp_dir) / "test_report.md"

        results = run_full_benchmark(
            data_dir="data",
            provider_name="mock",
            output_json_path=str(json_out),
            output_md_path=str(md_out),
            quiet=True,
        )

        assert results is not None
        assert isinstance(results, dict)

        # 1. Throughput & Volume
        assert results["metadata"]["total_records"] == 1000
        assert results["throughput"]["total_records_processed"] == 1000
        assert results["throughput"]["records_per_second"] > 500

        # 2. Reconciliation Correctness
        rc = results["reconciliation_correctness"]
        assert rc["total_cases"] == 1000
        assert rc["resolved_cases"] == 820
        assert rc["correctly_resolved_cases"] == 780
        assert rc["deterministic_resolution_coverage"] == 0.82
        assert rc["deterministic_correctness_rate"] == 0.9512
        assert rc["classification_accuracy"] == 0.939
        assert rc["payment_linkage_f1"] == 1.0
        assert rc["settlement_linkage_f1"] >= 0.94

        # 3. Exception Detection
        ed = results["exception_detection"]
        assert ed["true_positives"] == 220
        assert ed["true_negatives"] == 780
        assert ed["false_positives"] == 0
        assert ed["false_negatives"] == 0
        assert ed["precision"] == 1.0
        assert ed["recall"] == 1.0
        assert ed["f1"] == 1.0

        # 4. Policy Routing
        pr = results["policy_routing"]["counts"]
        assert pr["AUTO_RESOLVE"] == 780
        assert pr["AI_INVESTIGATION"] == 50
        assert pr["HUMAN_REVIEW"] == 40
        assert pr["ESCALATE"] == 130

        # 5. Financial Exposure Aggregates
        fe = results["financial_exposure"]
        assert fe["total_financial_exposure_identified"] == 1109091.50
        assert fe["exposure_resolved"] == 0.0
        assert fe["exposure_under_ai_investigation"] == 1.0
        assert fe["exposure_human_review"] == 249960.00
        assert fe["exposure_escalated"] == 859130.50
        assert fe["maximum_single_case_exposure"]["financial_impact"] == 49999.00
        assert fe["maximum_single_case_exposure"]["case_id"] == "CASE-000846"

        # 6. AI Investigation Subset (50 cases)
        ai = results["ai_investigation_subset"]
        assert ai["total_ai_cases"] == 50
        assert ai["finding_accuracy"] == 1.0
        assert ai["linkage_accuracy"] == 1.0
        assert ai["average_tool_calls_per_case"] >= 5.0
        assert ai["safety_metrics"]["unauthorized_action_count"] == 0

        # 7. File Artifacts Generated
        assert json_out.exists()
        assert md_out.exists()

        with open(json_out, "r", encoding="utf-8") as f:
            saved_json = json.load(f)
            assert saved_json["metadata"]["total_records"] == 1000

        with open(md_out, "r", encoding="utf-8") as f:
            saved_md = f.read()
            assert "# ReconGuard — System Evaluation & Benchmark Report" in saved_md
            assert "1,000 Cases" in saved_md
            assert "₹1,109,091.50" in saved_md


def test_financial_exposure_sum_consistency():
    """Verify that financial exposure sums across decisions equal total exposure."""
    results = run_full_benchmark(data_dir="data", quiet=True)
    fe = results["financial_exposure"]

    sum_decisions = (
        fe["exposure_resolved"]
        + fe["exposure_under_ai_investigation"]
        + fe["exposure_human_review"]
        + fe["exposure_escalated"]
    )
    assert round(sum_decisions, 2) == round(fe["total_financial_exposure_identified"], 2)


def test_markdown_report_formatting():
    """Verify that the markdown report generator produces clean, comprehensive markdown."""
    results = run_full_benchmark(data_dir="data", quiet=True)
    md = generate_markdown_report(results)

    assert "## 1. Executive Summary" in md
    assert "## 2. Policy Routing & Triage Distribution" in md
    assert "## 3. Financial Exposure Analysis" in md
    assert "## 4. Reconciliation Correctness & Exception Detection" in md
    assert "## 5. AI Investigation Subset Evaluation" in md
    assert "## 6. System Throughput & Execution Latency" in md
    assert "## 7. Safety Invariants Verification" in md
    assert "₹1,109,091.50" in md

