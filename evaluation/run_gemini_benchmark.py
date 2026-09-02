"""Reproducible AI Investigator benchmark harness.

Dynamically selects the operational dataset's current AI_INVESTIGATION-designated
cases (via the real matching engine + policy engine -- no hardcoded case IDs),
runs each one through a chosen LLMProvider, and writes a single structured JSON
artifact recording per-case telemetry plus honest, denominator-explicit summary
metrics.

This script is what was missing behind `evaluation/results/day6_gemini_evaluation.json`:
that file's numbers are real (verified against live Google API error payloads
embedded in it), but no committed script could reproduce how it was produced.
This harness closes that gap. It does NOT replay, reuse, or fabricate any
numbers from that file -- every run against `--provider gemini` makes real,
quota-consuming API calls against whatever Gemini model you specify.

Usage:
    # Free, offline dry run against the deterministic mock provider.
    # Use this to sanity-check the harness or CI without touching Gemini quota.
    python -m evaluation.run_gemini_benchmark --provider mock

    # Real live Gemini benchmark. Consumes Gemini API quota. Requires
    # GEMINI_API_KEY to be set in the environment.
    python -m evaluation.run_gemini_benchmark --provider gemini --model gemini-2.5-flash

    # Quota-constrained smoke test: only run the first N selected cases.
    python -m evaluation.run_gemini_benchmark --provider gemini --limit 5

Output:
    A JSON file under evaluation/results/ (path configurable via --output)
    with a `summary` block and a `cases` array. See `run_benchmark()` below
    for the exact schema.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.investigator.agent import InvestigatorAgent
from app.investigator.providers import GeminiProvider, LLMProvider, MockProvider
from app.investigator.tools import InvestigationToolRegistry
from app.investigator.types import FindingTaxonomy, InvestigationContext, InvestigationStatus
from app.matching.engine import ReconciliationEngine
from app.policy.queue import ExceptionQueue
from app.policy.types import ExceptionCase

# Maps each AI_INVESTIGATION scenario to the finding a correct investigation
# should reach. Mirrors the scoring logic already used by
# app/investigator/evaluator.py:AIEvaluator, kept local here so this harness
# is self-contained and doesn't require touching investigator internals.
_EXPECTED_FINDING_BY_SCENARIO = {
    "ROUNDING_VARIANCE": FindingTaxonomy.VERIFIED_ROUNDING_VARIANCE,
    "REFERENCE_MISMATCH": FindingTaxonomy.VERIFIED_REFERENCE_TYPO,
    "MISSING_INVOICE": FindingTaxonomy.MISSING_INVOICE_CONFIRMED,
}


def select_ai_investigation_cases(data_dir: str = "data") -> list[ExceptionCase]:
    """Dynamically select the current AI_INVESTIGATION-designated cases from the
    operational dataset. No case IDs are hardcoded anywhere in this function --
    selection is entirely a byproduct of running the real, deterministic
    matching engine and policy engine, identical to how the production API
    path routes cases into the AI investigator queue.
    """
    engine = ReconciliationEngine.from_csv_directory(data_dir)
    match_results = engine.reconcile_all()
    queue = ExceptionQueue.from_engine_results(match_results)
    return queue.get_ai_investigation_cases()


def build_provider(provider_name: str, model_name: str | None) -> LLMProvider:
    """Construct the requested provider. Does not silently fall back --
    an unavailable Gemini provider (missing API key) is only detected once
    `.investigate()` is called, and this harness records that as a failed
    case rather than crashing the whole run."""
    if provider_name == "mock":
        return MockProvider()
    if provider_name == "gemini":
        kwargs: dict[str, Any] = {}
        if model_name:
            kwargs["model_name"] = model_name
        return GeminiProvider(**kwargs)
    raise ValueError(f"Unknown provider '{provider_name}'. Use 'mock' or 'gemini'.")


def run_benchmark(
    provider_name: str = "mock",
    model_name: str | None = None,
    data_dir: str = "data",
    limit: int | None = None,
    max_iterations: int = 6,
) -> dict[str, Any]:
    """Run the AI_INVESTIGATION benchmark and return a structured report dict.

    Every case is attempted independently; a provider error/exception on one
    case is recorded as a FAILED case and does not abort the run, so a
    quota-exhausted live Gemini run still produces a complete, honest artifact
    (mirroring how day6_gemini_evaluation.json handled its 45 quota failures).
    """
    cases = select_ai_investigation_cases(data_dir)
    if limit is not None:
        cases = cases[:limit]

    tools = InvestigationToolRegistry.from_csv_directory(data_dir)
    provider = build_provider(provider_name, model_name)
    agent = InvestigatorAgent(tools=tools, provider=provider, max_iterations=max_iterations)

    scenario_counts: dict[str, int] = {}
    for c in cases:
        ext = c.exception_type.value if hasattr(c.exception_type, "value") else str(c.exception_type)
        scenario_counts[ext] = scenario_counts.get(ext, 0) + 1

    per_case_records: list[dict[str, Any]] = []
    completed = 0
    failed = 0
    inconclusive = 0
    correct_findings_overall = 0
    correct_findings_completed = 0
    correct_linkages_overall = 0

    for case in cases:
        context = InvestigationContext.from_exception_case(case)
        ext = case.exception_type.value if hasattr(case.exception_type, "value") else str(case.exception_type)
        expected_finding = _EXPECTED_FINDING_BY_SCENARIO.get(ext)

        t0 = time.perf_counter()
        try:
            result = agent.investigate(context)
            call_error: str | None = None
        except Exception as exc:
            # A provider can raise before even entering its own try/except
            # (e.g. GeminiProvider.investigate() raises ValueError immediately
            # if GEMINI_API_KEY is unset). Caught here so one misconfigured
            # run still produces a complete, honest artifact for all cases.
            result = None
            call_error = str(exc)
        latency = time.perf_counter() - t0

        if result is None:
            failed += 1
            per_case_records.append({
                "case_id": case.case_id,
                "order_id": case.order_id,
                "exception_type": ext,
                "policy_decision": case.decision.value,
                "candidate_payment_ids": list(case.payment_ids),
                "candidate_settlement_ids": list(case.settlement_ids),
                "provider": provider.provider_name,
                "investigation_status": "FAILED",
                "finding": None,
                "confidence": 0.0,
                "requires_human_review": True,
                "tool_call_count": 0,
                "iterations": 0,
                "latency_seconds": round(latency, 4),
                "error": call_error,
            })
            continue

        if result.investigation_status == InvestigationStatus.COMPLETED:
            completed += 1
        elif result.investigation_status == InvestigationStatus.FAILED:
            failed += 1
        if result.investigation_status == InvestigationStatus.INCONCLUSIVE or result.finding == FindingTaxonomy.INCONCLUSIVE:
            inconclusive += 1

        is_correct_finding = expected_finding is not None and result.finding == expected_finding
        if is_correct_finding:
            correct_findings_overall += 1
            if result.investigation_status == InvestigationStatus.COMPLETED:
                correct_findings_completed += 1

        if (
            set(result.supporting_payment_ids) == set(case.payment_ids)
            and set(result.supporting_settlement_ids) == set(case.settlement_ids)
        ):
            correct_linkages_overall += 1

        error_field = None
        if isinstance(result.evidence, dict):
            error_field = result.evidence.get("error")

        per_case_records.append({
            "case_id": case.case_id,
            "order_id": case.order_id,
            "exception_type": ext,
            "policy_decision": case.decision.value,
            "candidate_payment_ids": list(case.payment_ids),
            "candidate_settlement_ids": list(case.settlement_ids),
            "provider": result.provider_used,
            "investigation_status": result.investigation_status.value,
            "finding": result.finding.value,
            "confidence": round(result.confidence, 4),
            "requires_human_review": result.requires_human_review,
            "tool_call_count": len(result.tool_trace),
            # NOTE: neither this harness nor the current agent/provider
            # implementation separately tracks LLM round-trips distinct from
            # tool-call count. "iterations" is reported as an alias of
            # tool_call_count -- it is intentionally NOT a fabricated,
            # independently-measured metric. See the audit report for detail.
            "iterations": len(result.tool_trace),
            "latency_seconds": round(latency, 4),
            "error": error_field,
            "root_cause": result.root_cause,
            "recommendation": result.recommendation,
            "tool_trace": [t.to_dict() for t in result.tool_trace],
        })

    total = len(cases)
    completion_rate = completed / total if total else 0.0
    finding_accuracy_overall = correct_findings_overall / total if total else 0.0
    finding_accuracy_among_completed = (
        correct_findings_completed / completed if completed else 0.0
    )
    linkage_accuracy_overall = correct_linkages_overall / total if total else 0.0

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider.provider_name,
        "model_used": getattr(provider, "model_name", None),
        "total_cases_attempted": total,
        "completed_cases": completed,
        "failed_or_quota_limited_cases": failed,
        "inconclusive_cases": inconclusive,
        "completion_rate": round(completion_rate, 4),
        "finding_accuracy_overall": round(finding_accuracy_overall, 4),
        "finding_accuracy_among_completed": round(finding_accuracy_among_completed, 4),
        "linkage_accuracy_overall": round(linkage_accuracy_overall, 4),
        "scenario_distribution": scenario_counts,
        "reporting_note": (
            "'_overall' metrics use total_cases_attempted as the denominator and are "
            "NOT inflated by cases that failed or were quota-limited. "
            "'_among_completed' metrics use only completed_cases as the denominator. "
            "Always report both together -- never headline the '_among_completed' "
            "figure alone as overall model accuracy."
        ),
    }

    return {"summary": summary, "cases": per_case_records}


def main() -> None:
    parser = argparse.ArgumentParser(description="ReconGuard AI Investigator benchmark harness.")
    parser.add_argument(
        "--provider", choices=["mock", "gemini"], default="mock",
        help="Which LLMProvider to benchmark. 'mock' is free and offline; 'gemini' consumes real API quota.",
    )
    parser.add_argument(
        "--model", default=None,
        help="Override Gemini model name (only used with --provider gemini). "
             "Defaults to GeminiProvider's own default if omitted.",
    )
    parser.add_argument("--data-dir", default="data")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Only run the first N dynamically-selected cases (useful for quota-limited smoke tests).",
    )
    parser.add_argument("--max-iterations", type=int, default=6)
    parser.add_argument(
        "--output", default=None,
        help="Output JSON path. Defaults to evaluation/results/<provider>_benchmark_<timestamp>.json",
    )
    args = parser.parse_args()

    report = run_benchmark(
        provider_name=args.provider,
        model_name=args.model,
        data_dir=args.data_dir,
        limit=args.limit,
        max_iterations=args.max_iterations,
    )

    if args.output:
        out_path = Path(args.output)
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = Path("evaluation/results") / f"{args.provider}_benchmark_{ts}.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    s = report["summary"]
    print(f"Benchmark complete: {s['completed_cases']}/{s['total_cases_attempted']} completed "
          f"({s['completion_rate']*100:.1f}%), provider={s['provider']}, model={s['model_used']}")
    print(f"Artifact written to: {out_path}")


if __name__ == "__main__":
    main()
