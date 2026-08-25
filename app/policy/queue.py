"""Exception Queue Service for ReconGuard.

Manages, indexes, and queries ExceptionCase instances produced by the PolicyEngine.
Provides fast querying by decision, priority, exception type, and order ID.
"""

from collections import Counter, defaultdict
from typing import Any

from app.matching.types import MatchResult
from app.policy.engine import PolicyEngine
from app.policy.types import CasePriority, ExceptionCase, ExceptionType, PolicyDecision


class ExceptionQueue:
    """In-memory index and query queue for reconciliation exception cases."""

    def __init__(self, cases: list[ExceptionCase] | None = None):
        self._cases: list[ExceptionCase] = []
        self._by_case_id: dict[str, ExceptionCase] = {}
        self._by_order_id: dict[str, ExceptionCase] = {}
        self._by_decision: dict[PolicyDecision, list[ExceptionCase]] = defaultdict(list)
        self._by_priority: dict[CasePriority, list[ExceptionCase]] = defaultdict(list)
        self._by_exception_type: dict[ExceptionType, list[ExceptionCase]] = defaultdict(list)

        if cases:
            for case in cases:
                self.add_case(case)

    def add_case(self, case: ExceptionCase) -> None:
        """Add and index a case in the queue."""
        self._cases.append(case)
        self._by_case_id[case.case_id] = case
        self._by_order_id[case.order_id] = case
        self._by_decision[case.decision].append(case)
        self._by_priority[case.priority].append(case)
        self._by_exception_type[case.exception_type].append(case)

    @classmethod
    def from_engine_results(
        cls,
        match_results: list[MatchResult],
        policy_engine: PolicyEngine | None = None,
    ) -> "ExceptionQueue":
        """Process MatchResults through PolicyEngine and build an ExceptionQueue."""
        engine = policy_engine or PolicyEngine()
        cases = engine.evaluate_all(match_results)
        return cls(cases)

    @property
    def total_count(self) -> int:
        """Total number of cases in the queue."""
        return len(self._cases)

    def get_all_cases(self) -> list[ExceptionCase]:
        """Return all cases in the queue."""
        return list(self._cases)

    def get_case_by_id(self, case_id: str) -> ExceptionCase | None:
        """Look up a case by case_id."""
        return self._by_case_id.get(case_id)

    def get_case_by_order_id(self, order_id: str) -> ExceptionCase | None:
        """Look up a case by order_id."""
        return self._by_order_id.get(order_id)

    def get_cases_by_decision(self, decision: PolicyDecision | str) -> list[ExceptionCase]:
        """Retrieve all cases matching a specific PolicyDecision."""
        dec_enum = PolicyDecision(decision) if isinstance(decision, str) else decision
        return list(self._by_decision.get(dec_enum, []))

    def get_cases_by_priority(self, priority: CasePriority | str) -> list[ExceptionCase]:
        """Retrieve all cases matching a specific CasePriority."""
        prio_enum = CasePriority(priority) if isinstance(priority, str) else priority
        return list(self._by_priority.get(prio_enum, []))

    def get_cases_by_exception_type(self, exception_type: ExceptionType | str) -> list[ExceptionCase]:
        """Retrieve all cases matching a specific ExceptionType."""
        type_enum = ExceptionType(exception_type) if isinstance(exception_type, str) else exception_type
        return list(self._by_exception_type.get(type_enum, []))

    def get_auto_resolve_cases(self) -> list[ExceptionCase]:
        """Retrieve all auto-resolved cases."""
        return self.get_cases_by_decision(PolicyDecision.AUTO_RESOLVE)

    def get_ai_investigation_cases(self) -> list[ExceptionCase]:
        """Retrieve all cases designated for AI investigation."""
        return self.get_cases_by_decision(PolicyDecision.AI_INVESTIGATION)

    def get_human_review_cases(self) -> list[ExceptionCase]:
        """Retrieve all cases designated for human operations review."""
        return self.get_cases_by_decision(PolicyDecision.HUMAN_REVIEW)

    def get_escalations(self) -> list[ExceptionCase]:
        """Retrieve all escalated cases."""
        return self.get_cases_by_decision(PolicyDecision.ESCALATE)

    def get_high_priority_cases(self) -> list[ExceptionCase]:
        """Retrieve all HIGH priority cases."""
        return self.get_cases_by_priority(CasePriority.HIGH)

    def get_summary(self) -> dict[str, Any]:
        """Produce an actionable breakdown summary of the exception queue."""
        decision_counts = {
            dec.value: len(self._by_decision.get(dec, []))
            for dec in PolicyDecision
        }
        priority_counts = {
            prio.value: len(self._by_priority.get(prio, []))
            for prio in CasePriority
        }
        exception_type_counts = {
            ext.value: len(self._by_exception_type.get(ext, []))
            for ext in ExceptionType
            if len(self._by_exception_type.get(ext, [])) > 0
        }

        impact_by_decision = {
            dec.value: round(sum(c.financial_impact for c in self._by_decision.get(dec, [])), 2)
            for dec in PolicyDecision
        }
        impact_by_priority = {
            prio.value: round(sum(c.financial_impact for c in self._by_priority.get(prio, [])), 2)
            for prio in CasePriority
        }

        total_impact = round(sum(c.financial_impact for c in self._cases), 2)

        return {
            "total_cases": len(self._cases),
            "decision_counts": decision_counts,
            "priority_counts": priority_counts,
            "exception_type_counts": exception_type_counts,
            "financial_impact_by_decision": impact_by_decision,
            "financial_impact_by_priority": impact_by_priority,
            "total_financial_exposure": total_impact,
        }

