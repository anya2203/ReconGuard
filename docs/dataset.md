# ReconGuard Dataset & Ground-Truth Specification

This document details the design, taxonomy, schema, and validation of the synthetic financial reconciliation dataset and its evaluation ground truth for **ReconGuard** (Razorpay Buildathon 2026).

---

## 1. Overview & Purpose

Reconciliation in production fintech systems requires evaluating both high-volume routine matches and complex, ambiguous edge cases. ReconGuard uses a deterministic synthetic dataset generator to produce realistic multi-source financial records:

- **Orders**: Merchant checkout transactions.
- **Payments**: Gateway payment capture records with UTR identifiers.
- **Settlements**: Bank payout records and batched settlements.
- **Invoices**: Tax and billing records with itemized GST lines.
- **Adjustments**: Chargebacks, refunds, and fee adjustments.
- **Ground Truth**: Fixed evaluation labels joining directly on business identifiers (`order_id`).

---

## 2. Reproducibility & Fixed Anchor Date

To ensure reproducible evaluations across different environments and runs without wall-clock time drift:

- **Seed**: `SEED = 42` (configurable via `--seed`).
- **Fixed Anchor Datetime**: `2026-08-01T00:00:00+00:00` (UTC).
- **Time Offsets**: All `created_at` and `settled_at` timestamps derive strictly from the anchor datetime and scenario rules. No dynamic `datetime.now()` calls affect scenario determination or timestamp generation.

Running the generator multiple times with the same seed produces identical dataset and ground truth files.

---

## 3. Target Distribution (78 / 12 / 10 Split)

For a benchmark size of **1,000 cases**, the dataset adheres to the target distribution:

| Resolution Category | Target % | Exact Cases | Actual % | Primary Handler |
|---|---|---|---|---|
| **Deterministic Resolution** | 78.0% | **780** | 78.0% | Rule Matching Engine |
| **Deterministic Escalation** | 12.0% | **120** | 12.0% | Rule Matching Engine |
| **AI Investigation** | 10.0% | **100** | 10.0% | AI Investigator (Read-Only) + Policy Engine |
| **Total** | 100.0% | **1,000** | 100.0% | |

---

## 4. AI Investigation Split: "Knowing When It Doesn't Know"

A critical requirement of ReconGuard is demonstrating that the AI investigator distinguishes between cases with sufficient corroborating evidence and cases where information is genuinely insufficient.

The **100 AI Investigation cases** are split into two 50-case subcategories:

### A. AI-Resolvable (50 cases / 5.0%)
- **Definition**: Complex scenarios where rules fail (e.g. fuzzy UTR OCR errors, fractional tax rounding, dropped invoice generation), but read-only evidence across other systems allows the AI to discover the root cause and recommend safe auto-resolution.
- **Ground Truth**: `expected_ai_investigation: True`, `expected_human_escalation: False`, `expected_resolution_class: "AI_INVESTIGATION"`.

### B. AI-Escalation (50 cases / 5.0%)
- **Definition**: Ambiguous or uncorroborated scenarios (e.g. conflicting duplicate payments for the same order, missing bank payouts, abandoned orders with unlinked manual debits). The AI investigates, verifies lack of evidence, and declines auto-resolution, escalating safely to human operations.
- **Ground Truth**: `expected_ai_investigation: True`, `expected_human_escalation: True`, `expected_resolution_class: "AI_INVESTIGATION"`.

---

## 5. Scenario Taxonomy (12 Scenarios)

| # | Scenario Name | Category | Cases | Outcome | Human Escalation | Description |
|---|---|---|---|---|---|---|
| 1 | `EXACT_MATCH` | Deterministic Resolution | 720 | `MATCHED` | `False` | 1:1 clean match across order, payment, settlement (T+1 SLA), and invoice. |
| 2 | `MULTI_ORDER_SETTLEMENT` | Deterministic Resolution | 60 | `MATCHED` | `False` | 20 batches of 3 orders consolidated under single bank settlement UTRs. |
| 3 | `AMOUNT_MISMATCH` | Deterministic Escalation | 30 | `DISCREPANCY_FOUND` | `True` | Payment amount significantly differs from order (e.g. ₹4,999 vs ₹3,499). |
| 4 | `DELAYED_SETTLEMENT` | Deterministic Escalation | 30 | `DISCREPANCY_FOUND` | `True` | Settlement completed 7 days after payment, exceeding policy SLA (5 days). |
| 5 | `MISSING_PAYMENT` | Deterministic Escalation | 30 | `UNMATCHED` | `True` | Fulfilled order has invoice but zero gateway payment was captured. |
| 6 | `CHARGEBACK_ADJUSTMENT` | Deterministic Escalation | 30 | `ADJUSTED` | `True` | Bank dispute/chargeback logged against captured payment. |
| 7 | `ROUNDING_MISMATCH` | AI Investigation (Resolvable) | 20 | `DISCREPANCY_FOUND` | `False` | Micro-variance (₹0.05) due to itemized GST line rounding; AI explains root cause. |
| 8 | `REFERENCE_TYPO` | AI Investigation (Resolvable) | 20 | `DISCREPANCY_FOUND` | `False` | Gateway UTR has transposed characters (e.g. `...12` vs `...21`); AI reconstructs match. |
| 9 | `MISSING_INVOICE` | AI Investigation (Resolvable) | 10 | `DISCREPANCY_FOUND` | `False` | Payment & settlement matched; invoice generation failed; AI verifies for backfill. |
| 10 | `AMBIGUOUS_CANDIDATE` | AI Investigation (Escalation) | 20 | `DISCREPANCY_FOUND` | `True` | Multiple successful payments exist for same order (retry); AI routes to ops. |
| 11 | `INSUFFICIENT_EVIDENCE` | AI Investigation (Escalation) | 20 | `UNMATCHED` | `True` | Abandoned order with unlinked manual debit; AI identifies missing context and escalates. |
| 12 | `MISSING_SETTLEMENT` | AI Investigation (Escalation) | 10 | `DISCREPANCY_FOUND` | `True` | Payment captured but payout record missing from bank feed; AI flags for banking ops. |

---

## 6. Multi-Order Settlement Batching

In real-world payment aggregation, payment aggregators settle multiple payments in a single bulk payout transfer. 

- **Structure**: 20 settlement batches (`SET-BATCH-0001` to `SET-BATCH-0020`), each containing 3 distinct orders/payments sharing the same batch UTR (`UTR-BATCH-0001` to `UTR-BATCH-0020`).
- **Mathematical Invariant**:
  $$\text{Settlement Amount} = \sum (\text{Payment Amounts}) - \sum (\text{Gateway Fees})$$
- Each order in the batch has a distinct ground-truth entry tracking its membership in the batch.

---

## 7. Relational Schema Integrity & Orphan Handling

The database models (`Payment` and `Invoice`) enforce non-nullable foreign keys referencing `orders.order_id`. To preserve full referential integrity while representing orphan/missing-record scenarios:

1. **Missing Payment / Missing Invoice / Missing Settlement**:
   - The parent `Order` is generated in `orders.csv`, but no corresponding record is created in `payments.csv`, `invoices.csv`, or `settlements.csv`. No foreign key constraints are violated.
2. **Ambiguous Duplicate Candidate Payments**:
   - Multiple `Payment` records reference the same valid `order_id`.
3. **Insufficient Evidence / Abandoned Orders**:
   - The `Order` record exists with status `ABANDONED`, linked to manual adjustment records via `related_id = order_id`.

---

## 8. Ground-Truth Data Schema

Ground truth is stored in `data/ground_truth/ground_truth.csv` and `data/ground_truth/ground_truth.json`:

```csv
ground_truth_id,order_id,expected_scenario,expected_outcome,expected_resolution_class,expected_root_cause,expected_human_escalation,expected_ai_investigation,expected_confidence_band,expected_financial_impact,notes
```

- **`ground_truth_id`**: Dedicated namespace (`GT-000001` to `GT-001000`).
- **`order_id`**: Stable business identifier for joins (`ORD-000001` to `ORD-001000`).
- **`expected_resolution_class`**: `AUTO_RESOLVED` \| `DETERMINISTIC_ESCALATION` \| `AI_INVESTIGATION` \| `HUMAN_ESCALATION`.
- **`expected_outcome`**: `MATCHED` \| `DISCREPANCY_FOUND` \| `UNMATCHED` \| `ADJUSTED`.
- **`expected_root_cause`**: Standardized root-cause identifier.
- **`expected_human_escalation`**: Boolean (`True` / `False`).
- **`expected_ai_investigation`**: Boolean (`True` / `False`).
- **`expected_confidence_band`**: `HIGH` \| `MEDIUM` \| `LOW` \| `NONE`.
- **`expected_financial_impact`**: Numeric financial exposure amount in INR.

---

## 9. Usage & Validation Commands

### Generate Dataset
```bash
python -m app.services.data_generator
```

### Validate Dataset
```bash
python -m app.services.data_generator --validate
```

### Run Test Suite
```bash
pytest -q
```

