"""InvestigatorAgent orchestrating the AI investigation workflow."""

import time
from typing import Any

from app.investigator.providers import LLMProvider, MockProvider
from app.investigator.tools import InvestigationToolRegistry
from app.investigator.types import (
    FindingTaxonomy,
    InvestigationContext,
    InvestigationResult,
    InvestigationStatus,
)
from app.policy.types import ExceptionCase, PolicyDecision


class InvestigatorAgent:
    """Read-only evidence-driven AI Investigation Agent for complex reconciliation cases."""

    def __init__(
        self,
        tools: InvestigationToolRegistry,
        provider: LLMProvider | None = None,
        max_iterations: int = 6,
    ):
        self.tools = tools
        self.provider = provider or MockProvider()
        self.max_iterations = max_iterations

    def investigate(self, context: InvestigationContext) -> InvestigationResult:
        """Execute read-only investigation on a single case context."""
        # Safety gate: Validate case is designated for AI investigation
        if context.policy_decision != PolicyDecision.AI_INVESTIGATION.value:
            return InvestigationResult(
                case_id=context.case_id,
                order_id=context.order_id,
                finding=FindingTaxonomy.ESCALATE_TO_HUMAN,
                root_cause=f"Case policy decision '{context.policy_decision}' is not designated for AI investigation.",
                evidence={"policy_decision": context.policy_decision},
                confidence=1.0,
                recommendation="Recommend routing to appropriate operational workflow; bypass AI investigator. No financial action was taken by the investigator.",
                requires_human_review=True,
                investigation_status=InvestigationStatus.COMPLETED,
                provider_used=self.provider.provider_name,
            )

        # Delegate investigation loop to provider
        return self.provider.investigate(
            context=context,
            tools=self.tools,
            max_iterations=self.max_iterations,
        )

    def investigate_case(self, case: ExceptionCase) -> InvestigationResult:
        """Investigate an ExceptionCase instance."""
        context = InvestigationContext.from_exception_case(case)
        return self.investigate(context)

    def investigate_all(self, cases: list[ExceptionCase]) -> list[InvestigationResult]:
        """Investigate a batch of ExceptionCases in deterministic sequence."""
        return [self.investigate_case(c) for c in cases]

