# ReconGuard Dashboard — Visual Walkthrough & Screenshots

> **This directory is reserved for judge-facing screenshots and visual captures of the ReconGuard Finance Controller interface.**

---

## Recommended Screenshots for Buildathon Presentation

| Filename | View / Target | Key Elements to Showcase |
| :--- | :--- | :--- |
| `01-dashboard-overview.png` | Overview Dashboard (`/`) | Controller Health bar (0 Financial Writes), 5 KPI Cards (1,000 processed, 780 auto-resolved, ₹1.1M exposure), Benchmark Telemetry card, and Curated Scenario Launchers. |
| `02-exception-queue.png` | Operational Case Explorer (`/cases`) | High-density 1,000-case table, 1-click Preset Filter Chips, Control Owner column (`ENGINE`, `AI AGENT`, `OPS DESK`, `DISPUTE DESK`), and INR Financial Exposure callouts. |
| `03-ai-investigation-case.png` | Hero AI Case Detail (`/cases/CASE-000921`) | UTR Transposition Discrepancy Pinpoint (`...12` vs `...21`), 5-Stage Transaction Chain, AI Safety Boundary Panel (Read-only tools), and Autonomous AI Stepper. |
| `04-human-escalation-case.png` | Dispute Escalation Case (`/cases/CASE-000853`) | High-risk Chargeback Anomaly, Escalation Desk assignment (`DISPUTE_DESK`), Deterministic Policy SOP Next Action, and Exposure valuation. |
| `05-audit-trail.png` | Immutable Audit Timeline | Chronological event trace with color-coded badges (`DETERMINISTIC`, `AI`, `HUMAN`), exact UTC timestamps, and zero secret leakage. |

---

## How to Capture Live UI Screenshots Locally

1. Start the FastAPI backend:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. Start the Vite React frontend:
   ```bash
   cd frontend
   npm run dev
   ```
3. Open `http://localhost:3000` in your browser.
4. Capture high-resolution PNGs at `1920x1080` (16:9) and place them in this directory.

