# ReconGuard — Buildathon Judge FAQ

---

### Q1: Why not use an end-to-end LLM agent to reconcile all financial records?
**A**: End-to-end LLMs are non-deterministic, expensive, slow, and prone to hallucinations on tabular math. In financial reconciliation, 82% of records can be verified with mathematical certainty using deterministic algorithms in <50ms. ReconGuard uses deterministic algorithms for high-volume matching and reserves AI exclusively for unstructured ambiguity resolution (e.g. cross-referencing transposed UTRs or omitted invoice feeds).

---

### Q2: Can the AI Investigator mutate financial ledgers, trigger payouts, or execute refunds?
**A**: **No.** ReconGuard enforces a zero financial write boundary. All 8 operational tools in `InvestigationToolRegistry` are strictly read-only query interfaces. The backend FastAPI application contains **0 financial mutation endpoints**. AI findings are structured advisory recommendations accompanied by full tool execution traces; final financial execution remains under external human/system control.

---

### Q3: What happens when the AI provider (e.g. Google Gemini) fails, times out, or hits rate limits?
**A**: ReconGuard enforces the safety invariant: *"AI failure must never become financial-control failure."* When a model call encounters HTTP 429 quota exhaustion, network timeout, or malformed JSON, the investigation immediately yields `INCONCLUSIVE` (confidence: 0.0), routes the case to `OPERATIONS_DESK` for manual review, records the failure event in the audit trail, and preserves active financial exposure. The system never falls back to `AUTO_RESOLVE`.

---

### Q4: Is the AI accuracy really 100%?
**A**: We make **no general claim of 100% live-AI accuracy**. The 100% finding accuracy metric reported in the benchmark belongs to the deterministic `MockProvider` evaluation across the 50 AI test cases. During live evaluation against Google Gemini Free Tier, 5 completed cases achieved 100% accuracy, but the remaining 45 cases were rate-limited (HTTP 429). This real-world limitation is honestly documented and visible in the dashboard.

---

### Q5: Is the data used in the benchmark real production banking data?
**A**: **No.** ReconGuard evaluates against a controlled, synthetic operational dataset of 1,000 transactions modeling 13 realistic operational scenarios (clean exact matches, character transpositions, sub-cent GST rounding variances, batch settlements, gateway delays, omitted invoices, chargebacks, and refunds). Synthetic data allows exact, objective ground-truth evaluation without privacy or confidentiality risks.

---

### Q6: What does the "₹1,109,091.50 Total Financial Exposure" metric represent?
**A**: It represents the gross monetary variance identified and accounted for across all active exception cases (discrepancies, missing payments, unlinked settlements, chargebacks, and refunds) across the 1,000-case dataset. It is **not money recovered**; it is the total volume of financial risk isolated and brought under controller governance.

---

### Q7: How does ReconGuard prevent ground-truth data leakage during reconciliation?
**A**: The operational reconciliation engine, 12-branch policy engine, and AI investigator have zero access to `data/ground_truth/`. Ground truth labels are stored separately and are only ingested by `evaluation/run_benchmark.py` post-execution for objective accuracy and F1 score scoring. This isolation is verified by automated AST static analysis tests in our test suite.

---

### Q8: What are the three provider options available in the UI?
**A**:
1. **`DEMO REPLAY` (`demo_replay`)**: Guaranteed deterministic walkthrough designed for live judge presentations without quota risk. Explicitly labeled `DEMO REPLAY (PRE-RECORDED)`.
2. **`MOCK PROVIDER` (`mock`)**: High-speed offline simulation for test suites and benchmark reproduction.
3. **`LIVE GEMINI` (`gemini`)**: Live Google GenAI SDK multi-turn function calling with real-world rate-limit handling.

