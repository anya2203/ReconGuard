# ReconGuard — Audit Trail & Financial Control Evidence

> **Immutable, chronological audit logging providing complete end-to-end traceability for reconciliation exceptions, deterministic policy triage, and autonomous AI investigations.**

---

## 1. Core Principles & Financial Control Invariants

1. **Deterministic Guarantees First**: High-volume, structured transaction matching is performed by rule-based algorithms. Audit logs capture the exact deterministic matching method and confidence score.
2. **Policy-Governed**: The Policy Engine evaluates reconciliation results and assigns one of 4 deterministic routing tiers (`AUTO_RESOLVE`, `AI_INVESTIGATION`, `HUMAN_REVIEW`, `ESCALATE`).
3. **Read-Only AI Investigations**: AI is invoked strictly for cases routed to `AI_INVESTIGATION`. Audit records capture all read-only tools consulted and corroborated findings without storing hidden prompts, API keys, or full chain-of-thought traces.
4. **Append-Only & Read-Only**: Audit history is strictly immutable from the API. No endpoints exist to update, edit, or delete audit events.
5. **Non-Blocking Persistence**: If database persistence fails or encounters a connection issue, it is logged safely without modifying or crashing the underlying reconciliation decision or policy action.

---

## 2. Audit Event Types & Actors

| Event Action | Triggering Actor | Event Source | Description & Context Payload |
| :--- | :--- | :---: | :--- |
| `RECONCILIATION_COMPLETED` | `RECONCILIATION_ENGINE` | `DETERMINISTIC` | Emitted when matching engine finishes evaluating order, payment, and settlement feeds. Contains `status`, `match_method`, `match_confidence`, and `discrepancy_reason`. |
| `POLICY_DECISION` | `POLICY_ENGINE` | `DETERMINISTIC` | Emitted when policy engine applies risk categorization. Contains `decision`, `priority`, `exception_type`, `financial_impact`, `reason`, and `explanation`. |
| `AI_INVESTIGATION_STARTED` | `AI_INVESTIGATOR` | `AI` | Emitted when read-only AI investigation begins on an eligible case. Contains `provider`, `order_id`, and `reason`. |
| `AI_INVESTIGATION_COMPLETED` | `AI_INVESTIGATOR` | `AI` | Emitted when AI agent corroborates evidence and completes structured finding. Contains `finding`, `confidence`, `root_cause`, `tools_called`, and `recommendation`. |
| `AI_INVESTIGATION_FAILED` | `AI_INVESTIGATOR` | `AI` | Emitted when AI investigation fails, is rate-limited, or produces inconclusive findings. Triggers subsequent escalation to operations desk. |
| `HUMAN_REVIEW_REQUIRED` | `OPERATIONS_POLICY` | `HUMAN` | Emitted for `HUMAN_REVIEW`, `ESCALATE`, or inconclusive AI cases. Contains `financial_impact`, `next_action`, and `required_desk` (`OPERATIONS_DESK` or `DISPUTE_DESK`). |

---

## 3. Retrieving Audit Trails via API

### Endpoint: `GET /api/audit/{case_id}`

Retrieves the complete, chronological audit history for a specific case:

```bash
curl -X GET http://127.0.0.1:8000/api/audit/CASE-000921
```

**Example JSON Response**:

```json
{
  "case_id": "CASE-000921",
  "order_id": "ORD-000921",
  "total_events": 4,
  "events": [
    {
      "audit_id": "AUD-CASE-000921-001",
      "case_id": "CASE-000921",
      "actor": "RECONCILIATION_ENGINE",
      "action": "RECONCILIATION_COMPLETED",
      "source": "DETERMINISTIC",
      "details_json": {
        "source": "DETERMINISTIC",
        "status": "DISCREPANCY",
        "match_method": "REFERENCE_FUZZY",
        "match_confidence": 0.85,
        "order_id": "ORD-000921",
        "discrepancy_reason": "Payment UTR UTR-IND-00092112 does not match Settlement UTR UTR-IND-00092121",
        "financial_impact": 0.0
      },
      "timestamp": "2026-09-03T20:47:00.000000+00:00"
    },
    {
      "audit_id": "AUD-CASE-000921-002",
      "case_id": "CASE-000921",
      "actor": "POLICY_ENGINE",
      "action": "POLICY_DECISION",
      "source": "DETERMINISTIC",
      "details_json": {
        "source": "DETERMINISTIC",
        "decision": "AI_INVESTIGATION",
        "priority": "LOW",
        "exception_type": "REFERENCE_MISMATCH",
        "financial_impact": 0.0,
        "reason": "Reference mismatch with identical amounts; AI investigation routed to verify UTR transposition."
      },
      "timestamp": "2026-09-03T20:47:00.000100+00:00"
    },
    {
      "audit_id": "AUD-CASE-000921-003",
      "case_id": "CASE-000921",
      "actor": "AI_INVESTIGATOR",
      "action": "AI_INVESTIGATION_STARTED",
      "source": "AI",
      "details_json": {
        "source": "AI",
        "provider": "mock",
        "order_id": "ORD-000921"
      },
      "timestamp": "2026-09-03T20:47:05.000000+00:00"
    },
    {
      "audit_id": "AUD-CASE-000921-004",
      "case_id": "CASE-000921",
      "actor": "AI_INVESTIGATOR",
      "action": "AI_INVESTIGATION_COMPLETED",
      "source": "AI",
      "details_json": {
        "source": "AI",
        "provider": "mock",
        "finding": "VERIFIED_REFERENCE_TYPO",
        "confidence": 0.96,
        "root_cause": "UTR character transposition between Gateway and Bank Settlement file",
        "recommendation": "Approve settlement linkage; reference variance verified.",
        "tools_called": [
          "lookup_order",
          "lookup_payment",
          "lookup_settlement",
          "lookup_invoice",
          "lookup_adjustments"
        ],
        "tool_count": 5
      },
      "timestamp": "2026-09-03T20:47:06.000000+00:00"
    }
  ]
}
```

---

## 4. Viewing the Audit Trail in Frontend UI

1. Open the ReconGuard dashboard at `http://127.0.0.1:3000`.
2. Navigate to any case from the **Case Explorer** (e.g. `CASE-000921`, `CASE-000001`, or `CASE-000853`).
3. Scroll down to the **"Audit Trail & Financial Control Evidence"** section.
4. The timeline displays all chronological events with clear source badges (`DETERMINISTIC`, `AI`, `HUMAN`), exact timestamps, financial exposure figures, and consulted tool calls.

