# ReconGuard — System Evaluation & Benchmark Report

> **Comprehensive performance, accuracy, exception classification, and financial exposure evaluation of the ReconGuard reconciliation pipeline.**

---

## 1. Executive Summary

| Evaluation Dimension | Result | Methodology & Scope |
| :--- | :---: | :--- |
| **Total Operational Dataset** | **1,000 Cases** | 1,000 synthetic orders across 13 operational scenarios |
| **Deterministic Resolution Coverage** | **82.00%** | 820 of 1,000 cases resolved by deterministic engine |
| **Deterministic Correctness Rate** | **95.12%** | 780 of 820 engine-resolved cases confirmed clean |
| **Outcome Classification Accuracy** | **93.90%** | Evaluated against independent 1,000-case ground truth |
| **Payment Entity Linkage F1** | **100.00%** | Perfect 1:1 and 1:N payment identification |
| **Settlement Entity Linkage F1** | **94.84%** | High-precision settlement batch reconciliation |
| **Deterministic Throughput Speed** | **In-Memory Benchmark** | Single-process, in-memory benchmark measurement; throughput is runtime-dependent and is not a production scalability claim |
| **MockProvider Self-Consistency (50 Cases)** | **50 / 50 (100.00%)** | Deterministic harness self-consistency check; not live LLM generalization |

---

## 2. Policy Routing & Triage Distribution

The Policy Engine evaluates deterministic matching outputs and routes cases across 4 operational tiers:

| Policy Tier | Case Count | Proportion | Total Exposure | Operational Action |
| :--- | :---: | :---: | :---: | :--- |
| **`AUTO_RESOLVE`** | **780** | **78.0%** | ₹0.00 | Instant automated ledger clearance |
| **`AI_INVESTIGATION`** | **50** | **5.0%** | ₹1.00 | Autonomous read-only evidence corroboration |
| **`HUMAN_REVIEW`** | **40** | **4.0%** | ₹249,960.00 | Operations desk candidate triage queue |
| **`ESCALATE`** | **130** | **13.0%** | ₹859,130.50 | High-risk dispute and fraud escalation desk |
| **Total** | **1,000** | **100.0%** | **₹1,109,091.50** | 100% volume accounted |

---

## 3. Financial Exposure Analysis

> **Terminology Note**: "Financial exposure identified" denotes the total monetary variance or disputed amount flagged for operational attention. ReconGuard does not claim automated money recovery without human/system approval.

- **Total Financial Exposure Identified**: **₹1,109,091.50**
- **Exposure Resolved (Auto-Resolve)**: **₹0.00** (780 clean matches)
- **Exposure Under AI Investigation**: **₹1.00** (subtle rounding variances & UTR typos)
- **Exposure in Operations Queue (Human Review)**: **₹249,960.00**
- **Exposure in Escalation Desk**: **₹859,130.50** (high-risk disputes & large amount anomalies)
- **Average Exposure per Exception Case**: **₹5,041.32**
- **Maximum Single-Case Exposure**: **₹49,999.00** (Case `CASE-000846`, Order `ORD-000846`)

### Exposure Breakdown by Priority
- **HIGH Priority** (170 cases): **₹1,109,090.50**
- **MEDIUM Priority** (30 cases): **₹0.00**
- **LOW Priority** (800 cases): **₹1.00**

---

## 4. Reconciliation Correctness & Exception Detection

### A. Binary Exception Detection Matrix
- **True Positives (Exceptions Detected)**: 220
- **True Negatives (Clean Matches Resolved)**: 780
- **False Positives (Clean Matches Flagged)**: 0
- **False Negatives (Exceptions Missed)**: 0
- **Detection Precision**: **100.00%**
- **Detection Recall**: **100.00%**
- **Detection F1 Score**: **100.00%**

### B. Outcome Confusion Matrix

```json
{
  "MATCHED": {
    "MATCHED": 780,
    "AMBIGUOUS": 0,
    "DISCREPANCY": 0,
    "UNMATCHED": 0
  },
  "DISCREPANCY": {
    "DISCREPANCY": 115,
    "MATCHED": 40,
    "AMBIGUOUS": 21,
    "UNMATCHED": 0
  },
  "UNMATCHED": {
    "UNMATCHED": 44,
    "AMBIGUOUS": 0,
    "DISCREPANCY": 0,
    "MATCHED": 0
  },
  "AMBIGUOUS": {
    "AMBIGUOUS": 0,
    "DISCREPANCY": 0,
    "MATCHED": 0,
    "UNMATCHED": 0
  }
}
```

### C. Deterministic Resolution Breakdown
- **Engine Matched Records**: 820 / 1000 (82.00% coverage)
- **Correct Clean Resolutions**: 780 / 820 (95.12% correctness)
- **Engine Matches with Subtle Discrepancies**: 40 cases (20 UTR typos + 20 rounding variances; isolated by Policy Engine and safely routed to AI Investigation).

---

## 5. AI Investigation Subset Evaluation (50 Cases)

The AI Investigator is evaluated **strictly on the 50 cases routed to `AI_INVESTIGATION`**.

- **Evaluated Provider**: `MOCK`
- **Total AI-Designated Cases**: 50
- **Investigation Finding Accuracy**: **100.00%**
- **Recommendation Accuracy**: **100.00%**
- **Entity Linkage Accuracy**: **100.00%**
- **Average Tool Calls per Case**: **6.00 read-only tool calls**
- **Average Execution Latency**: **0.0001s**
- **Unauthorized Financial Mutations**: **0 (100% compliant)**

### Live Gemini Benchmark Reality & Provider Limitations
> *During the live Gemini 3.6 Flash evaluation across 50 cases, 5 investigations completed before the Google API Free Tier per-minute quota was exhausted (HTTP 429). All 5 completed investigations produced correct findings (100%) and valid entity linkages (100%). The remaining 45 cases were safely rate-limited and escalated rather than misclassified.*

---

## 6. System Throughput & Execution Latency

- **Total Operational Records**: 1,000
- **Benchmark Scope**: Single-process, in-memory benchmark measurement; throughput is runtime-dependent and is not a production scalability claim.

---

## 7. Safety Invariants Verification

- **Financial Write Endpoints**: **0** (no `PUT`, `DELETE`, or mutating `POST` routes).
- **Database Mutation Tools**: **0** (all 8 investigator tools are strictly read-only lookups).
- **Ground-Truth Isolation**: **Verified** via AST static analysis tests (`tests/test_api.py`).
- **AI Recommendation Guardrails**: All recommendations explicitly state that no financial action was executed by the AI investigator.

---

*Report generated automatically by `evaluation/run_benchmark.py` at 2026-09-04T07:35:20.313024+00:00.*
