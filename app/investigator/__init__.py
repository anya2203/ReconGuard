"""ReconGuard AI Investigator Module.

Provides read-only, evidence-driven AI investigation agents for complex reconciliation cases.
"""

from app.investigator.agent import InvestigatorAgent
from app.investigator.evaluator import AIEvaluationReport, AIEvaluator, AISafetyMetrics
from app.investigator.providers import GeminiProvider, LLMProvider, MockProvider
from app.investigator.tools import InvestigationToolRegistry
from app.investigator.types import (
    FindingTaxonomy,
    InvestigationContext,
    InvestigationResult,
    InvestigationStatus,
    ToolCallRecord,
)

__all__ = [
    "FindingTaxonomy",
    "InvestigationStatus",
    "ToolCallRecord",
    "InvestigationContext",
    "InvestigationResult",
    "InvestigationToolRegistry",
    "LLMProvider",
    "MockProvider",
    "GeminiProvider",
    "InvestigatorAgent",
    "AIEvaluator",
    "AIEvaluationReport",
    "AISafetyMetrics",
]

