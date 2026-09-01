"""Pydantic schemas for AI Investigation API."""

from typing import Any
from pydantic import BaseModel, Field


class InvestigationRequest(BaseModel):
    """Payload to trigger an AI investigation on an eligible case."""

    provider: str = Field("mock", description="LLM provider: 'mock' (default offline simulation) or 'gemini' (live API)")


class ToolCallRecordSchema(BaseModel):
    """Schema for individual tool calls recorded during investigation."""

    tool_name: str = Field(..., description="Name of the read-only operational tool executed")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Input parameters passed to the tool")
    result_summary: dict[str, Any] = Field(default_factory=dict, description="Structured result returned by the tool")
    timestamp: str = Field(..., description="Timestamp of execution")


class InvestigationResponse(BaseModel):
    """Structured AI investigation result and recommendation."""

    case_id: str
    order_id: str
    finding: str = Field(..., description="Finding taxonomy enum")
    root_cause: str = Field(..., description="Plaintext root cause explanation")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Corroborated evidence bundle")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")
    recommendation: str = Field(..., description="Actionable next step recommendation (advisory only)")
    requires_human_review: bool = Field(..., description="Whether human review is required")
    supporting_payment_ids: list[str] = Field(default_factory=list)
    supporting_settlement_ids: list[str] = Field(default_factory=list)
    supporting_invoice_id: str | None = None
    investigation_status: str = Field(..., description="Status: COMPLETED, INCONCLUSIVE, or FAILED")
    tool_trace: list[ToolCallRecordSchema] = Field(default_factory=list)
    provider_used: str = Field("mock", description="Provider used: 'mock' or 'gemini'")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")


class InvestigationListResponse(BaseModel):
    """List response of completed investigations."""

    total: int
    investigations: list[InvestigationResponse]

