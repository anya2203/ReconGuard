"""Pydantic response schemas for Dashboard API."""

from pydantic import BaseModel, Field


class DashboardSummaryResponse(BaseModel):
    """High-level summary KPIs and metrics for the reconciliation dashboard."""

    total_cases: int = Field(..., description="Total number of reconciliation cases processed")
    auto_resolved: int = Field(..., description="Cases automatically resolved by deterministic matching")
    ai_investigation: int = Field(..., description="Complex discrepancy cases routed to AI investigation")
    human_review: int = Field(..., description="Edge cases routed to human operations review")
    escalated: int = Field(..., description="High-risk exceptions escalated to specialized desks")
    total_financial_exposure: float = Field(..., description="Total financial value of active exceptions in INR")
    high_priority_cases: int = Field(..., description="Number of HIGH priority exception cases")
    medium_priority_cases: int = Field(..., description="Number of MEDIUM priority exception cases")
    low_priority_cases: int = Field(..., description="Number of LOW priority exception cases")
    matched_cases: int = Field(..., description="Number of MATCHED transactions from matching engine")
    unmatched_cases: int = Field(..., description="Number of UNMATCHED transactions from matching engine")
    discrepancy_cases: int = Field(..., description="Number of DISCREPANCY transactions from matching engine")
    ambiguous_cases: int = Field(..., description="Number of AMBIGUOUS candidate transactions from matching engine")
    financial_impact_by_decision: dict[str, float] = Field(..., description="Total monetary exposure grouped by policy decision")
    financial_impact_by_priority: dict[str, float] = Field(..., description="Total monetary exposure grouped by case priority")
    exception_type_counts: dict[str, int] = Field(..., description="Breakdown count of cases by exception category")

