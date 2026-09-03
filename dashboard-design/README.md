# ReconGuard — AI Finance Controller Dashboard

> **Design specification, information architecture, and operational UX documentation for the ReconGuard reconciliation and financial-control interface.**

---

## 1. Product Overview & Purpose

ReconGuard is a financial reconciliation and exception-control platform built for high-volume fintech and payment operations teams.

The dashboard gives finance and operations controllers real-time visibility into:
- **Reconciliation Health**: Throughput and match distribution across payment, settlement, invoice, and adjustment records.
- **Exception Volume & Triage**: Clear categorization of clean matches vs. operational anomalies.
- **Financial Exposure**: Real-time monetary valuation of open discrepancies and disputed amounts.
- **Autonomous AI Investigations**: Read-only evidence collection and root-cause corroboration for ambiguous reference and rounding variances.
- **Human Control Queues**: Structured escalation desks for high-risk disputes, chargebacks, and unresolvable variances.
- **Immutable Audit Trails**: End-to-end chronological timeline of all system and human actions.

---

## 2. Core Architectural UX Flow

The ReconGuard interface is architected around a strict hierarchy:

$$\text{Deterministic Facts} \longrightarrow \text{Read-Only AI Investigation} \longrightarrow \text{Policy-Governed Human Control}$$

```
Financial Records (Orders, Payments, Settlements, Invoices, Adjustments)
                                ↓
                 Deterministic Reconciliation Engine
                                ↓
                     Deterministic Policy Engine
                                ↓
┌───────────────────────────────┬─────────────────────────────────┐
│       AUTO RESOLVE            │         AMBIGUOUS CASE          │
│  (78% Clean Ledger Clearing)  │               ↓                 │
│                               │     AI Investigation Agent      │
│                               │      (Read-Only Evidence)       │
│                               │               ↓                 │
└───────────────────────────────┴───────────────┬─────────────────┘
                                                ↓
                                    Human / Desk Control
                                  (Operations & Risk Queue)
                                                ↓
                                     Immutable Audit Trail
```

- **Deterministic systems** establish proven financial facts across 1:1, fuzzy, and batch aggregation algorithms.
- **AI investigators** corroborate ambiguous exceptions using strictly read-only operational tools without write authority.
- **Policy rules** dictate operational routing tiers and prevent unapproved financial mutations.
- **Humans and external systems** retain exclusive control over high-risk financial decisions.

---

## 3. Dashboard Functional Sections

### A. Controller Overview
Executive command center providing:
- **5 Core KPI Cards**: Records Processed (`1,000`), Auto-Resolved (`780`), AI Investigation (`50`), Human/Escalated (`170`), and Total Financial Exposure Identified (`₹1,109,091.50`).
- **Controller Health Bar**: Real-time indicators showing Reconciliation (`HEALTHY`), Policy Engine (`DETERMINISTIC`), AI Investigator (`READ-ONLY`), Audit Trail (`ACTIVE`), and Financial Writes (`0 MUTATIONS`).
- **Verified Benchmark Telemetry**: Live Phase 1 benchmark metrics (93.90% accuracy, 95.12% deterministic correctness, 6,136.6 rec/sec throughput).
- **Curated Demo Scenarios Launcher**: 1-click walkthroughs for Hero AI Case (`CASE-000921`), Baseline Clean Match (`CASE-000001`), and Dispute Escalation (`CASE-000853`).

### B. Operational Exception Queue (`/cases`)
High-density triage table with multi-criteria filtering:
- **Control Owner Indicators**: Explicit badges indicating whether a case is governed by `ENGINE`, `AI AGENT`, `OPS DESK`, or `DISPUTE DESK`.
- **1-Click Filter Presets**: Instant filtering for All Cases, AI Investigation, Human Review, Escalated, and High Priority.
- **Financial Exposure Callouts**: Formatted INR monetary values for instant risk prioritization.

### C. Case Detail Experience (`/cases/:caseId`)
Comprehensive exception investigation view featuring:
- **Executive Snapshot Header**: Expected Order Amount vs. Actual Settlement Payout vs. Identified Financial Variance.
- **Discrepancy Pinpoint Callout**: Exact character comparison for reference transposition (e.g. `...12` vs `...21`).
- **5-Stage Transaction Lifecycle Chain**: Visual status across Order $\rightarrow$ Payment $\rightarrow$ Settlement $\rightarrow$ Invoice $\rightarrow$ Adjustments.
- **AI Safety & Control Boundary**: Explicit disclosure of permitted read-only tools vs. prohibited financial mutations.
- **Inline Multi-Turn AI Investigator**: Live function-calling stepper with finding taxonomy, confidence score, and advisory recommendations.
- **Immutable Audit Trail**: Chronological timeline of all system and human events with color-coded source badges (`DETERMINISTIC`, `AI`, `HUMAN`).

### D. Standalone AI Investigations Registry (`/investigations`)
Centralized repository of all AI investigation runs, evidence traces, and ordered tool-calling histories.

---

## 4. AI Safety & Control Boundary

```
┌─────────────────────────────────────────────────────────────┐
│             AI INVESTIGATOR SAFETY BOUNDARY                 │
│              (Access: Strictly Read-Only)                   │
├──────────────────────────────┬──────────────────────────────┤
│  PERMITTED READ-ONLY TOOLS   │ PROHIBITED FINANCIAL ACTIONS │
├──────────────────────────────┼──────────────────────────────┤
│ ✓ lookup_order               │ ✕ Cannot modify records      │
│ ✓ lookup_payment             │ ✕ Cannot change ledger       │
│ ✓ lookup_settlement          │ ✕ Cannot override policy     │
│ ✓ lookup_invoice             │ ✕ Cannot issue refunds       │
│ ✓ lookup_adjustments         │ ✕ Cannot initiate payouts    │
│ ✓ compare_records            │ ✕ Cannot approve mutations   │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 5. Directory Contents

- [`information-architecture.md`](./information-architecture.md) — Navigation structure, routing hierarchy, and component relationships.
- [`dashboard-spec.md`](./dashboard-spec.md) — Comprehensive technical specification for every dashboard component.
- [`screenshots/`](./screenshots/README.md) — Recommended judge walkthrough screenshots.

