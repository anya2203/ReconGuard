# ReconGuard — Pitch Outline

> **Buildathon Track**: Track 04 — AI Finance Controller  
> **Tagline**: Deterministic-First AI Finance Controller for Payment Reconciliation & Exception Resolution

---

## 1. The Hook (0:00 – 0:45)
- **The Reality of Fintech Ops**: High-growth merchants process hundreds of thousands of transactions daily across orders, payment gateways, bank settlement files, billing tax invoices, and refunds.
- **The Reconciliation Dilemma**:
  - *Brittle Rule Systems*: Rigid scripts break on simple reference typos, omitted invoices, or sub-cent GST rounding variances, burying finance teams in thousands of manual exception tickets.
  - *Unconstrained LLM Wrappers*: Putting generative AI in charge of ledger writes risks hallucinations, non-deterministic balances, and catastrophic financial liabilities.
- **The Solution**: **ReconGuard** — A deterministic-first, policy-governed architecture where deterministic algorithms handle high-volume math, an AI agent investigates ambiguous discrepancies using read-only tools, and humans control all financial writes.

---

## 2. Product Architecture & Innovation (0:45 – 2:00)

### Layer 1: Deterministic Reconciliation Engine
- Processes **3,000+ records/sec** across 4 specialized matching strategies:
  - Exact 1:1 Matcher
  - Duplicate Capture Detector
  - 1:N Aggregation Matcher
  - Temporal Levenshtein Fuzzy Matcher
- Resolves **82.0%** of operational volume straight-through with **zero AI overhead or cost**.

### Layer 2: 12-Branch Deterministic Policy Engine
- Decides operational routing based on financial exposure and risk tier:
  - `AUTO_RESOLVE` (780 cases / ₹0.00 exposure)
  - `AI_INVESTIGATION` (50 cases / ₹1.00 exposure)
  - `HUMAN_REVIEW` (40 cases / ₹249,960.00 exposure)
  - `ESCALATE` (130 cases / ₹859,130.50 exposure)

### Layer 3: Read-Only AI Investigator Agent
- Equipped with **8 strictly read-only operational tools** to query orders, payments, settlements, invoices, and adjustments.
- Corroborates complete evidence chains (e.g. gateway vs bank UTR typos, GST rounding discrepancies) and outputs structured advisory findings.
- **Zero Write Authority**: The AI cannot mutate balances, trigger refunds, or alter ledgers.

### Layer 4: Append-Only Financial Audit Trail
- Every transaction lifecycle event, policy classification, AI tool execution, and human desk action is recorded chronologically in an immutable audit timeline.

---

## 3. Resilience & Real-World Safety (2:00 – 3:15)
- **The Core Invariant**: *"AI failure must never become financial-control failure."*
- **Fail-Safe Degradation**: If the AI provider is rate-limited (HTTP 429), times out, or encounters malformed output, the system fails safely:
  $$\text{AI Failure} \longrightarrow \text{INCONCLUSIVE} \longrightarrow \text{OPERATIONS\_DESK Triage} \longrightarrow \text{Zero Financial Mutations}$$
- **100% Transparent Provider Modes**:
  - `Live Gemini`: Live Google GenAI SDK function calling with real-world quota handling.
  - `Mock Provider`: Offline deterministic benchmark evaluation.
  - `Demo Replay`: Guaranteed, transparent demonstration mode for judge walkthroughs.

---

## 4. Benchmark & Impact (3:15 – 4:15)
- **Evaluated on 1,000 Synthetic Cases Modeling 13 Real-World Anomaly Scenarios**:
  - **93.90%** Classification Accuracy
  - **95.12%** Deterministic Correctness Rate
  - **100.00%** Payment Linkage F1 Score
  - **94.84%** Settlement Linkage F1 Score
  - **₹1,109,091.50** Total Financial Exposure Identified & Accounted
  - **179 Automated Tests Passing** (100% test pass rate)

---

## 5. Conclusion & The Takeaway (4:15 – 5:00)
- **Summary**: ReconGuard reconciles what can be proven, investigates what is ambiguous, and keeps high-risk financial actions under strict policy and human control.

