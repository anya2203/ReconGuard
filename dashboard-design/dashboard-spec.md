# ReconGuard Dashboard — Component Specification

> **Detailed technical specification for all UI components, data contracts, control boundaries, and security guarantees across the ReconGuard dashboard.**

---

## 1. Master Component Matrix

| Component | Purpose | Target Persona | Backend Data Source | Control Classification | Safety Boundary Guarantee |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Mission & Philosophy Banner** | Establishes core system thesis in 10 seconds | VP Finance, Auditor | Static text | Informational | Clear demarcation that AI does not execute money movements |
| **Controller Health Bar** | Live verification of system safety invariants | Risk Controller, Judge | `ReconciliationService` state | `DETERMINISTIC` | Confirms 0 financial mutations and 12-branch policy rule enforcement |
| **Primary KPI Cards** | High-level volume, resolution, and exposure metrics | Operations Lead | `GET /api/dashboard/summary` | `DETERMINISTIC` | Direct aggregation of engine outcomes; no fabricated numbers |
| **Benchmark Telemetry Card** | Verified evaluation accuracy, F1 scores, throughput | Lead Engineer, Judge | `GET /api/dashboard/benchmark` | `DETERMINISTIC` | Evaluated against independent 1,000-case ground truth; honest AI rate-limit disclosure |
| **Curated Demo Scenarios** | 1-click launcher for key operational archetypes | Judge, Demo Presenter | Static routing to `/cases/:id` | Mixed | Navigates to verified baseline (`CASE-000001`), AI hero (`CASE-000921`), and dispute (`CASE-000853`) |
| **Financial Exposure Summary** | Monetary impact breakdown by policy decision and priority | Head of Treasury | `GET /api/dashboard/summary` | `DETERMINISTIC` | Accurately calculates active discrepancy exposure in INR |
| **Operational Exception Queue** | High-throughput filtering and triage across 1,000 cases | Triage Specialist | `GET /api/cases` | Policy-Governed | Clear Control Owner badges (`ENGINE`, `AI AGENT`, `OPS DESK`, `DISPUTE DESK`) |
| **Executive Variance Header** | Instant 360° summary of expected vs. actual variance | Lead Controller | `GET /api/cases/:id` | `DETERMINISTIC` | Highlights exact variance and required human action |
| **Transaction Lifecycle Chain** | Visual 5-entity operational feed tracing | Investigator | `GET /api/cases/:id` | `DETERMINISTIC` | Read-only entity linking (Order $\rightarrow$ Payment $\rightarrow$ Settlement $\rightarrow$ Invoice $\rightarrow$ Adjustments) |
| **AI Safety Boundary Panel** | Explicit permission disclosure for AI agent | Auditor, Compliance Officer | Static security definition | `AI` / Policy Boundary | Declares 8 read-only tools vs. 5 strictly prohibited mutation actions |
| **AI Investigation Stepper** | Multi-turn function calling execution and finding display | Investigator | `POST /api/cases/:id/investigate` | `AI` (Read-Only) | Zero raw prompt/chain-of-thought storage; structured finding taxonomy and confidence |
| **Audit Trail Timeline** | Chronological immutable lifecycle history | Compliance Officer, Auditor | `GET /api/audit/:id` | `DETERMINISTIC` + `AI` + `HUMAN` | Append-only; zero mutation endpoints (`POST/PUT/DELETE /api/audit` rejected) |

---

## 2. Detailed Component Specifications

### 2.1. Controller Health (`ControllerHealth.tsx`)
- **File**: [`frontend/src/components/dashboard/ControllerHealth.tsx`](file:///c:/Users/User1/Documents/ReconGuard/frontend/src/components/dashboard/ControllerHealth.tsx)
- **Key Metrics Displayed**:
  - `RECONCILIATION`: `HEALTHY` (4 matching algorithms: Exact, Fuzzy, Aggregation, Duplicate)
  - `POLICY ENGINE`: `DETERMINISTIC` (12 decision branches)
  - `AI INVESTIGATOR`: `READ-ONLY` (8 inspection tools, max 6 iterations)
  - `AUDIT TRAIL`: `ACTIVE` (Immutable append-only)
  - `FINANCIAL WRITES`: `0 MUTATIONS` (Zero write authority)
- **Safety Guarantee**: Communicates to judges that the system is an audited control layer, not an autonomous agent with open write permissions.

### 2.2. Verified Benchmark Telemetry (`BenchmarkMetricsCard.tsx`)
- **File**: [`frontend/src/components/dashboard/BenchmarkMetricsCard.tsx`](file:///c:/Users/User1/Documents/ReconGuard/frontend/src/components/dashboard/BenchmarkMetricsCard.tsx)
- **Backend Endpoint**: `GET /api/dashboard/benchmark`
- **Fields Displayed**:
  - `classification_accuracy`: **93.90%** (1,000 cases evaluated against ground truth)
  - `deterministic_correctness`: **95.12%** (780 / 820 clean matches verified)
  - `binary_exception_f1`: **100.00%** (Perfect binary exception detection)
  - `payment_linkage_f1`: **100.00%** (Exact payment identity linking)
  - `settlement_linkage_f1`: **94.84%** (Batch settlement reconciliation)
  - `ai_mock_evaluation_accuracy`: **100.00%** (50 cases evaluated via MockProvider)
  - `deterministic_throughput_rps`: **6,136.6 rec/sec** (Deterministic engine speed)
- **Honest AI Limitation Note**:
  - *"5 completed before Free Tier HTTP 429 quota exhaustion (100% finding accuracy, 100% linkage accuracy; 45 rate-limited and escalated). The system is feature-frozen with deterministic fallback to prevent silent LLM failures."*

### 2.3. AI Safety & Control Boundary (`AIBoundaryPanel.tsx`)
- **File**: [`frontend/src/components/investigation/AIBoundaryPanel.tsx`](file:///c:/Users/User1/Documents/ReconGuard/frontend/src/components/investigation/AIBoundaryPanel.tsx)
- **Permitted Read-Only Capabilities (✓)**:
  1. `lookup_order` — Read checkout amount, currency, customer, and timestamp.
  2. `lookup_payment` — Read gateway status, authorization code, and payment UTR.
  3. `lookup_settlement` — Read bank settlement payout batch, fees, and settlement UTR.
  4. `lookup_invoice` — Read GST tax invoice, tax amounts, and invoice state.
  5. `lookup_adjustments` — Read dispute, chargeback, or fee adjustment records.
  6. `compare_records` — Cross-entity attribute comparison.
- **Prohibited Write Mutations (✕)**:
  1. Cannot modify transaction records.
  2. Cannot alter accounting ledger balances.
  3. Cannot override deterministic policy rules.
  4. Cannot issue refunds or initiate bank payouts.
  5. Cannot approve high-risk exceptions.

### 2.4. Audit Trail Timeline (`AuditTrailTimeline.tsx`)
- **File**: [`frontend/src/components/audit/AuditTrailTimeline.tsx`](file:///c:/Users/User1/Documents/ReconGuard/frontend/src/components/audit/AuditTrailTimeline.tsx)
- **Backend Endpoint**: `GET /api/audit/:caseId`
- **Event Taxonomy & Actors**:
  - `RECONCILIATION_COMPLETED` (Actor: `RECONCILIATION_ENGINE`, Source: `DETERMINISTIC`)
  - `POLICY_DECISION` (Actor: `POLICY_ENGINE`, Source: `DETERMINISTIC`)
  - `AI_INVESTIGATION_STARTED` (Actor: `AI_INVESTIGATOR`, Source: `AI`)
  - `AI_INVESTIGATION_COMPLETED` (Actor: `AI_INVESTIGATOR`, Source: `AI`)
  - `AI_INVESTIGATION_FAILED` (Actor: `AI_INVESTIGATOR`, Source: `AI`)
  - `HUMAN_REVIEW_REQUIRED` (Actor: `OPERATIONS_POLICY`, Source: `HUMAN`)
- **Immutability Invariant**: Append-only log. The API layer provides zero write/mutation endpoints.

