# ReconGuard — Benchmark & Financial Exposure Evaluation Guide

This guide describes how to reproduce and run the end-to-end evaluation benchmark for ReconGuard.

---

## 1. Quickstart: Running the Benchmark

From the repository root:

```bash
# Standard reproducible offline benchmark (uses MockProvider for deterministic AI evaluation)
python evaluation/run_benchmark.py

# Or run as a Python module:
python -m evaluation.run_benchmark
```

### Optional Arguments

```bash
# Run with custom output paths
python evaluation/run_benchmark.py \
    --data-dir data \
    --output-json evaluation/results/benchmark_results.json \
    --output-md evaluation/results/benchmark_report.md

# Run live Gemini investigation benchmark across the 50 AI cases (Requires GEMINI_API_KEY)
python evaluation/run_benchmark.py --provider gemini
```

---

## 2. Evaluation Methodology & Pipeline Flow

The benchmark executes in 4 strictly isolated phases:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. RUN OPERATIONAL PIPELINE (Zero Ground-Truth Access)      │
│    ReconciliationEngine -> MatchResults -> PolicyEngine     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. POST-EXECUTION GROUND-TRUTH EVALUATION                   │
│    ReconciliationEvaluator compares outputs against         │
│    independent ground truth labels.                         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. AGGREGATE FINANCIAL EXPOSURE & RISK METRICS              │
│    Computes total exposure identified, exposure by decision,│
│    exposure by priority tier, and max single-case exposure. │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. AI INVESTIGATION SUBSET EVALUATION (50 Cases)            │
│    Evaluates autonomous evidence corroboration accuracy     │
│    and tool-call execution traces on AI-designated cases.   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Evaluated Metrics Summary

### A. Reconciliation Correctness
- **Total Cases**: 1,000 operational records.
- **Deterministic Resolution Coverage**: **82.00%** (820 / 1,000 cases resolved by deterministic algorithms in <0.2s).
- **Deterministic Correctness Rate**: **95.12%** (780 / 820 resolved cases confirmed clean).
- **Classification Accuracy**: **93.90%** (939 / 1,000 cases).
- **Payment Linkage F1**: **100.00%**.
- **Settlement Linkage F1**: **94.84%**.

### B. Binary Exception Detection
- **True Positives**: 220 (all true exception cases detected).
- **True Negatives**: 780 (clean matches auto-resolved).
- **False Positives**: 0.
- **False Negatives**: 0.
- **Precision, Recall & F1**: **100.00%**.

### C. Policy Routing Distribution
- **`AUTO_RESOLVE`**: 780 cases (78.0%).
- **`AI_INVESTIGATION`**: 50 cases (5.0%).
- **`HUMAN_REVIEW`**: 40 cases (4.0%).
- **`ESCALATE`**: 130 cases (13.0%).

### D. Aggregate Financial Exposure
- **Total Financial Exposure Identified**: **₹1,109,091.50**.
- **Exposure Resolved (Auto-Resolve)**: ₹0.00.
- **Exposure Under AI Investigation**: ₹1.00 (subtle sub-cent rounding variances).
- **Exposure in Operations Queue (Human Review)**: ₹249,960.00.
- **Exposure in Escalation Desk**: ₹859,130.50 (chargebacks and high-value discrepancies).
- **Average Exposure per Exception**: ₹5,041.32.
- **Maximum Single-Case Exposure**: ₹49,999.00 (`CASE-000846`).

---

## 4. Ground-Truth Isolation Guarantee

- **Zero Leakage**: Ground truth is stored in `data/ground_truth/` and is accessed **strictly after pipeline execution** for verification.
- **AST Static Analysis**: Verified via `tests/test_api.py` and `tests/test_benchmark.py` that matching algorithms, policy rules, AI investigator tools, and FastAPI services contain zero imports or access to ground-truth files.

---

## 5. Distinction Between Deterministic and AI Evaluation

- **Deterministic Evaluation**: Evaluates the full 1,000-case operational dataset processed by `ReconciliationEngine` (Exact, Fuzzy, Duplicate, and Aggregation matchers) and `PolicyEngine`.
- **AI Investigation Evaluation**: Evaluates **only the 50 cases** routed to `AI_INVESTIGATION`.
  - **MockProvider**: Provides a 100% reproducible, deterministic offline baseline.
  - **Gemini 3.6 Flash**: In live API benchmarking, 5 cases completed with 100% accuracy before provider Free Tier rate limits (HTTP 429) halted requests. Uncompleted cases are safely handled as human escalations without silent failures.

