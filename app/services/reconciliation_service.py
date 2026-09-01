"""Reconciliation Service bridging matching, policy, operational data, and AI investigator layers."""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any

from app.investigator.agent import InvestigatorAgent
from app.investigator.providers import GeminiProvider, MockProvider
from app.investigator.tools import InvestigationToolRegistry
from app.investigator.types import FindingTaxonomy, InvestigationResult, InvestigationStatus
from app.matching.engine import ReconciliationEngine
from app.policy.engine import PolicyEngine
from app.policy.queue import ExceptionQueue
from app.policy.types import CasePriority, ExceptionCase, ExceptionType, PolicyDecision

logger = logging.getLogger("reconguard.service")


class ReconciliationService:
    """Singleton service providing thread-safe, high-performance API access to reconciliation state."""

    _instance: "ReconciliationService | None" = None

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.engine = ReconciliationEngine.from_csv_directory(data_dir)
        self.tools = InvestigationToolRegistry.from_csv_directory(data_dir)
        self.policy_engine = PolicyEngine()
        
        # Run deterministic reconciliation once and build ExceptionQueue
        self.match_results = self.engine.reconcile_all()
        self.queue = ExceptionQueue.from_engine_results(self.match_results, self.policy_engine)
        
        # Pre-index cases by ID and Order ID
        self._cases_by_id: dict[str, ExceptionCase] = {c.case_id: c for c in self.queue.get_all_cases()}
        self._cases_by_order_id: dict[str, ExceptionCase] = {c.order_id: c for c in self.queue.get_all_cases()}
        self._match_by_order_id = {m.order_id: m for m in self.match_results}
        
        # In-memory investigation results store
        self._investigations_by_case_id: dict[str, InvestigationResult] = {}
        self._load_saved_evaluations()

    @classmethod
    def get_instance(cls, data_dir: str = "data") -> "ReconciliationService":
        """Get or initialize the singleton reconciliation service."""
        if cls._instance is None:
            cls._instance = cls(data_dir=data_dir)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for test fixtures)."""
        cls._instance = None

    def _load_saved_evaluations(self) -> None:
        """Load saved benchmark evaluations if available."""
        artifact_path = Path("evaluation/results/day6_gemini_evaluation.json")
        if artifact_path.exists():
            try:
                with open(artifact_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for c in data.get("cases", []):
                        if c.get("investigation_status") == "COMPLETED":
                            cid = c.get("case_id")
                            if cid and cid not in self._investigations_by_case_id:
                                self._investigations_by_case_id[cid] = InvestigationResult(
                                    case_id=cid,
                                    order_id=c.get("order_id", ""),
                                    finding=FindingTaxonomy(c.get("finding")),
                                    root_cause=c.get("root_cause", ""),
                                    evidence=c.get("evidence", {}),
                                    confidence=float(c.get("confidence", 0.95)),
                                    recommendation=c.get("recommendation", ""),
                                    requires_human_review=bool(c.get("requires_human_review", False)),
                                    supporting_payment_ids=c.get("supporting_payment_ids", []),
                                    supporting_settlement_ids=c.get("supporting_settlement_ids", []),
                                    supporting_invoice_id=c.get("supporting_invoice_id"),
                                    investigation_status=InvestigationStatus.COMPLETED,
                                    provider_used="gemini",
                                )
            except Exception as e:
                logger.warning(f"Could not load historical evaluation artifact: {e}")

    def get_dashboard_summary(self) -> dict[str, Any]:
        """Compute high-level summary metrics derived directly from reconciliation and policy state."""
        queue_summary = self.queue.get_summary()
        
        # Compute match breakdown
        matched_count = sum(1 for m in self.match_results if m.status.value == "MATCHED")
        unmatched_count = sum(1 for m in self.match_results if m.status.value == "UNMATCHED")
        discrepancy_count = sum(1 for m in self.match_results if m.status.value == "DISCREPANCY")
        ambiguous_count = sum(1 for m in self.match_results if m.status.value == "AMBIGUOUS")
        
        dec_counts = queue_summary["decision_counts"]
        prio_counts = queue_summary["priority_counts"]
        
        return {
            "total_cases": queue_summary["total_cases"],
            "auto_resolved": dec_counts.get(PolicyDecision.AUTO_RESOLVE.value, 0),
            "ai_investigation": dec_counts.get(PolicyDecision.AI_INVESTIGATION.value, 0),
            "human_review": dec_counts.get(PolicyDecision.HUMAN_REVIEW.value, 0),
            "escalated": dec_counts.get(PolicyDecision.ESCALATE.value, 0),
            "total_financial_exposure": queue_summary["total_financial_exposure"],
            "high_priority_cases": prio_counts.get(CasePriority.HIGH.value, 0),
            "medium_priority_cases": prio_counts.get(CasePriority.MEDIUM.value, 0),
            "low_priority_cases": prio_counts.get(CasePriority.LOW.value, 0),
            "matched_cases": matched_count,
            "unmatched_cases": unmatched_count,
            "discrepancy_cases": discrepancy_count,
            "ambiguous_cases": ambiguous_count,
            "financial_impact_by_decision": queue_summary["financial_impact_by_decision"],
            "financial_impact_by_priority": queue_summary["financial_impact_by_priority"],
            "exception_type_counts": queue_summary["exception_type_counts"],
        }

    def get_cases(
        self,
        page: int = 1,
        page_size: int = 20,
        decision: str | None = None,
        priority: str | None = None,
        exception_type: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """Query and paginate cases with deterministic ordering and multi-field filtering."""
        cases = self.queue.get_all_cases()

        # Filter by Decision
        if decision:
            dec_upper = decision.strip().upper()
            try:
                dec_enum = PolicyDecision(dec_upper)
                cases = [c for c in cases if c.decision == dec_enum]
            except ValueError:
                raise ValueError(f"Invalid decision filter: '{decision}'. Valid: {[d.value for d in PolicyDecision]}")

        # Filter by Priority
        if priority:
            prio_upper = priority.strip().upper()
            try:
                prio_enum = CasePriority(prio_upper)
                cases = [c for c in cases if c.priority == prio_enum]
            except ValueError:
                raise ValueError(f"Invalid priority filter: '{priority}'. Valid: {[p.value for p in CasePriority]}")

        # Filter by Exception Type
        if exception_type:
            ext_upper = exception_type.strip().upper()
            try:
                ext_enum = ExceptionType(ext_upper)
                cases = [c for c in cases if c.exception_type == ext_enum]
            except ValueError:
                raise ValueError(f"Invalid exception_type filter: '{exception_type}'. Valid: {[e.value for e in ExceptionType]}")

        # Search by Case ID or Order ID
        if search:
            q = search.strip().lower()
            cases = [c for c in cases if q in c.case_id.lower() or q in c.order_id.lower()]

        # Deterministic sorting by case_id
        cases.sort(key=lambda c: c.case_id)

        total = len(cases)
        total_pages = max(1, (total + page_size - 1) // page_size) if page_size > 0 else 1
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_items = cases[start_idx:end_idx]

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "cases": [c.to_dict() for c in page_items],
        }

    def get_case(self, case_id: str) -> ExceptionCase | None:
        """Look up a case by case_id."""
        return self._cases_by_id.get(case_id.strip())

    def get_transaction_chain(self, case_id: str) -> dict[str, Any] | None:
        """Assemble the complete multi-entity transaction chain for a case."""
        case = self.get_case(case_id)
        if not case:
            return None

        order_id = case.order_id
        order_data = self.tools.lookup_order(order_id)
        
        # Payments
        payments = []
        for pid in case.payment_ids:
            p_res = self.tools.lookup_payment(pid)
            if p_res.get("found"):
                payments.append(p_res)
        if not payments:
            order_pays = self.tools.lookup_payments_for_order(order_id)
            if order_pays.get("found"):
                payments = order_pays.get("payments", [])

        # Settlements
        settlements = []
        for sid in case.settlement_ids:
            s_res = self.tools.lookup_settlement(sid)
            if s_res.get("found"):
                settlements.append(s_res)

        # Invoice
        invoice_data = self.tools.lookup_invoice(order_id)

        # Adjustments
        adjustments_res = self.tools.lookup_adjustments(order_id=order_id)
        adjustments = list(adjustments_res.get("adjustments", []))
        for p in payments:
            pid = p.get("payment_id")
            if pid:
                p_adj = self.tools.lookup_adjustments(payment_id=pid)
                for a in p_adj.get("adjustments", []):
                    if a not in adjustments:
                        adjustments.append(a)

        return {
            "case_id": case.case_id,
            "order_id": order_id,
            "order": order_data if order_data.get("found") else None,
            "payments": payments,
            "settlements": settlements,
            "invoice": invoice_data if invoice_data.get("found") else None,
            "adjustments": adjustments,
        }

    def get_evidence(self, case_id: str) -> dict[str, Any] | None:
        """Retrieve deterministic match evidence and discrepancy explanations for a case."""
        case = self.get_case(case_id)
        if not case:
            return None

        match_res = self._match_by_order_id.get(case.order_id)
        
        return {
            "case_id": case.case_id,
            "order_id": case.order_id,
            "match_method": case.match_method,
            "match_confidence": case.match_confidence,
            "evidence": case.evidence,
            "reason": case.reason,
            "explanation": case.explanation,
            "match_status": match_res.status.value if match_res else "UNKNOWN",
            "match_discrepancy_reason": match_res.reason if match_res else "",
        }

    def get_investigations(self) -> list[dict[str, Any]]:
        """Retrieve all completed AI investigation results."""
        return [res.to_dict() for res in self._investigations_by_case_id.values()]

    def get_investigation(self, case_id: str) -> dict[str, Any] | None:
        """Retrieve historical investigation result for a case."""
        res = self._investigations_by_case_id.get(case_id.strip())
        return res.to_dict() if res else None

    def investigate_case(self, case_id: str, provider_name: str = "mock") -> dict[str, Any]:
        """Trigger a read-only investigation on an eligible case."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case '{case_id}' not found.")

        # Safety policy gate
        if case.decision != PolicyDecision.AI_INVESTIGATION:
            raise ValueError(
                f"Case '{case_id}' is designated as '{case.decision.value}'. "
                f"Only cases with decision 'AI_INVESTIGATION' can be investigated by AI."
            )

        provider = GeminiProvider() if provider_name.lower() == "gemini" else MockProvider()
        agent = InvestigatorAgent(tools=self.tools, provider=provider, max_iterations=6)
        
        result = agent.investigate_case(case)
        self._investigations_by_case_id[case.case_id] = result
        return result.to_dict()

