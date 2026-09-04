# ReconGuard — 5-Minute Judge Demo Script

> **Purpose**: Step-by-step timed demonstration script for Buildathon judges.  
> **Target Duration**: Exactly 5 minutes.  
> **Tone**: Confident, operational, technically grounded, and safety-first.

---

## [0:00 – 0:30] Step 1: The Problem & The Core Philosophy

- **Action**: Open browser at `http://127.0.0.1:3000` (ReconGuard Dashboard).
- **Spoken Script**:
  > *"Welcome to ReconGuard — the AI Finance Controller for payment reconciliation. In high-volume fintech operations, reconciling checkout orders against gateway captures, bank settlement files, tax invoices, and chargebacks is high-friction. Traditional rule systems break on simple typos, while pure LLM wrappers risk financial hallucinations.*
  > 
  > *ReconGuard’s thesis is simple: Deterministic systems guarantee financial correctness. AI handles ambiguity. The policy engine decides. Humans control high-risk financial actions."*

---

## [0:30 – 1:15] Step 2: Dashboard & Executive Controller Health

- **Action**: Highlight top KPI cards, Controller Health bar, and Benchmark Telemetry card on the Overview Page.
- **Spoken Script**:
  > *"Here on the Finance Controller Overview, we see the complete operational picture across 1,000 synthetic transactions:*
  > - *780 cases (78%) are straight-through exact matches with ₹0.00 exposure.*
  > - *50 cases (5%) have subtle, manageable discrepancies routed to AI investigation.*
  > - *40 cases (4%) require human operations triage.*
  > - *130 cases (13%) are high-risk disputes or macro variances escalated to dispute desks.*
  > - *Total identified financial exposure: ₹1,109,091.50.*
  > 
  > *Notice that 82% of all cases are resolved deterministically in milliseconds without invoking an AI model, keeping costs low and latency negligible."*

---

## [0:15 – 2:15] Step 3: Clean Deterministic Baseline (`CASE-000001`)

- **Action**: Navigate to Case Explorer, search `CASE-000001`, and click to open Case Detail.
- **Spoken Script**:
  > *"Let's look at `CASE-000001`. This represents a standard clean transaction. The order, payment capture, bank settlement, and tax invoice match 1:1 with exact amount and reference congruence.*
  > 
  > *The deterministic engine instantly assigns `AUTO_RESOLVE`. In the Audit Trail below, you can see the deterministic reconciliation and policy events recorded with zero AI involvement. No model was called, and no inference tokens were wasted."*

---

## [2:15 – 3:30] Step 4: The Hero AI Case — Reference Typo (`CASE-000921`)

- **Action**: Click the Hero Case preset chip on Case Explorer or navigate to `CASE-000921`.
- **Spoken Script**:
  > *"Now let's examine `CASE-000921` — our hero ambiguity case. Here, the Gateway Payment UTR is `UTR-IND-00092112`, but the Bank Settlement UTR is `UTR-IND-00092121`. A human or standard regex rule would flag this as an unlinked transaction.*
  > 
  > *Our Policy Engine isolates this as a reference discrepancy and routes it to the AI Investigator. Let's run the investigation using Demo Replay.*
  > 
  > *(Click 'Run AI Investigation')*
  > 
  > *Notice what just happened: The AI agent executed 6 read-only operational tool steps: looking up the order, payment, settlement, tax invoice, adjustments, and comparative diff. It corroborated that the amounts, timestamps, and customer entities match 100%, and correctly diagnosed `VERIFIED_REFERENCE_TYPO` at 96% confidence.*
  > 
  > *Crucially: The AI provided an advisory recommendation. It did NOT mutate the database, execute a payout, or alter the ledger. In the audit trail below, every single tool call is recorded with timestamps."*

---

## [3:30 – 4:15] Step 5: Real-World Resilience & Fail-Safe Degradation

- **Action**: Toggle provider to Live Gemini or simulate rate-limit failure in UI.
- **Spoken Script**:
  > *"What happens when the real world gets messy? If the live Gemini API is rate-limited (HTTP 429), times out, or returns invalid data, ReconGuard enforces a critical invariant:*
  > 
  > *'AI failure must never become financial-control failure.'*
  > 
  > *When an AI error occurs, the case immediately falls back to `INCONCLUSIVE`, requires human operations triage (`OPERATIONS_DESK`), preserves the ₹1.109M exposure without alterations, and records the failure in the append-only audit trail. The AI can NEVER auto-resolve an exception upon failure."*

---

## [4:15 – 5:00] Step 6: Benchmark Proof, Red-Team Validation & Closing

- **Action**: Point to the Benchmark Metrics Card and Terminal showing 179 passing tests.
- **Spoken Script**:
  > *"To prove reproducibility, ReconGuard includes an automated evaluation harness:*
  > - *93.90% Classification Accuracy across 1,000 cases.*
  > - *95.12% Deterministic Correctness.*
  > - *100% Payment Linkage F1.*
  > - *179 automated unit, integration, and adversarial red-team tests passing with 0 financial mutation endpoints.*
  > 
  > *ReconGuard reconciles what can be proven, investigates what is ambiguous, and keeps high-risk financial decisions strictly under policy and human control. Thank you."*

