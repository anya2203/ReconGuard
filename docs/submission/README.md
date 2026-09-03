# ReconGuard — Buildathon Submission Package

> **Track**: Track 04 — AI Finance Controller  
> **Project**: ReconGuard — Deterministic-First AI Finance Controller  
> **Repository**: [https://github.com/anya2203/ReconGuard](https://github.com/anya2203/ReconGuard)  
> **Evaluation Baseline**: 1,000 synthetic operational records | 179/179 automated tests passing

---

## 1. Submission Overview

ReconGuard is a hybrid financial reconciliation and exception investigation platform designed for high-volume fintech operations. It solves the critical tradeoff between deterministic financial accuracy and flexible ambiguity resolution.

### Core Value Thesis
> *"Deterministic systems guarantee financial correctness.  
> AI handles ambiguity.  
> The Policy Engine decides.  
> Humans control high-risk financial actions."*

---

## 2. Key Architecture & Control Summary

```
Operational Data Feeds (Orders, Payments, Settlements, Invoices, Adjustments)
                            ↓
  Deterministic Matching Engine (Exact, Duplicate, Aggregation, Fuzzy)
                            ↓
  Deterministic Policy Engine (12 explicit branches, 4 decisions)
    ├── AUTO_RESOLVE (82.0% coverage / 780 cases clean)
    ├── AI_INVESTIGATION (5.0% / 50 cases ambiguous)
    │     ├── 8 Read-Only Operational Tools
    │     ├── 3 Provider Options: Live Gemini, Mock, Demo Replay
    │     └── Graceful Fail-Safe: Rate limits/errors route to Human Review
    ├── HUMAN_REVIEW (4.0% / 40 cases operations triage)
    └── ESCALATE (13.0% / 130 cases high-risk dispute desk)
                            ↓
  Append-Only Audit Trail (Ordered chronological lifecycle records)
                            ↓
  Judge-Ready Finance Controller Dashboard (React 19 + TypeScript + Vite)
```

---

## 3. Key Submission Deliverables

| Document | Purpose |
| :--- | :--- |
| [`pitch-outline.md`](file:///c:/Users/User1/Documents/ReconGuard/docs/submission/pitch-outline.md) | Structured pitch deck & narrative summary |
| [`demo-script.md`](file:///c:/Users/User1/Documents/ReconGuard/docs/submission/demo-script.md) | 5-minute timed judge demonstration script |
| [`judge-faq.md`](file:///c:/Users/User1/Documents/ReconGuard/docs/submission/judge-faq.md) | Hard questions & defensible architectural answers |
| [`dashboard-design/`](file:///c:/Users/User1/Documents/ReconGuard/dashboard-design/README.md) | Information architecture and dashboard UX specifications |
| [`evaluation/run_benchmark.py`](file:///c:/Users/User1/Documents/ReconGuard/evaluation/run_benchmark.py) | Standalone reproducible benchmark script |

---

## 4. Key Performance & Safety Metrics

- **Deterministic Resolution Coverage**: **82.00%** (820 / 1,000 cases)
- **Deterministic Correctness**: **95.12%** (780 / 820 cases confirmed exact match)
- **Classification Accuracy**: **93.90%**
- **Payment Linkage F1**: **100.00%**
- **Settlement Linkage F1**: **94.84%**
- **Identified Financial Exposure**: **₹1,109,091.50** (strictly accounted across exception queues)
- **Financial Mutation Endpoints**: **0** (strictly read-only tools and zero write APIs)
- **Automated Test Suite**: **179 / 179 passing tests** (Pytest)

