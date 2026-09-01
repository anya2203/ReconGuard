"""Pydantic request and response schemas for Cases and Evidence API."""

from typing import Any
from pydantic import BaseModel, Field


class CaseSummary(BaseModel):
    """Compact summary of a reconciliation case for list views and tables."""

    case_id: str = Field(..., description="Unique reconciliation case identifier")
    order_id: str = Field(..., description="Merchant order identifier")
    decision: str = Field(..., description="Policy decision: AUTO_RESOLVE, AI_INVESTIGATION, HUMAN_REVIEW, ESCALATE")
    exception_type: str = Field(..., description="Exception category")
    priority: str = Field(..., description="Operational priority: HIGH, MEDIUM, LOW")
    financial_impact: float = Field(..., description="Monetary impact in INR")
    match_method: str = Field(..., description="Matching strategy applied")
    match_confidence: float = Field(..., description="Match confidence score between 0.0 and 1.0")
    payment_ids: list[str] = Field(default_factory=list, description="Linked payment IDs")
    settlement_ids: list[str] = Field(default_factory=list, description="Linked settlement IDs")
    invoice_id: str | None = Field(None, description="Linked invoice ID if present")
    adjustment_ids: list[str] = Field(default_factory=list, description="Linked adjustment IDs if present")
    requires_ai: bool = Field(False, description="Whether case is eligible for AI investigation")
    requires_human: bool = Field(False, description="Whether human review is required")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")


class CaseListResponse(BaseModel):
    """Paginated list response of reconciliation cases."""

    total: int = Field(..., description="Total number of matching cases")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total pages available")
    cases: list[CaseSummary] = Field(..., description="Array of case summaries")


class TransactionChainOrder(BaseModel):
    """Order checkout entity in the transaction chain."""

    order_id: str
    customer_id: str | None = None
    amount: float
    currency: str = "INR"
    status: str | None = None
    created_at: str | None = None


class TransactionChainPayment(BaseModel):
    """Gateway payment entity in the transaction chain."""

    payment_id: str
    order_id: str | None = None
    amount: float
    currency: str = "INR"
    status: str | None = None
    payment_method: str | None = None
    utr: str | None = None
    created_at: str | None = None


class TransactionChainSettlement(BaseModel):
    """Bank payout settlement entity in the transaction chain."""

    settlement_id: str
    payment_id: str | None = None
    amount: float
    fee: float = 0.0
    tax: float = 0.0
    net_amount: float
    utr: str | None = None
    status: str | None = None
    settled_at: str | None = None


class TransactionChainInvoice(BaseModel):
    """Billing invoice entity in the transaction chain."""

    invoice_id: str
    order_id: str
    amount: float
    tax_amount: float = 0.0
    status: str | None = None
    created_at: str | None = None


class TransactionChainAdjustment(BaseModel):
    """Dispute or refund adjustment entity in the transaction chain."""

    adjustment_id: str
    type: str | None = None
    amount: float
    related_id: str | None = None
    reason: str | None = None
    created_at: str | None = None


class TransactionChain(BaseModel):
    """Complete multi-entity lifecycle trace from checkout to bank settlement."""

    case_id: str
    order_id: str
    order: TransactionChainOrder | None = None
    payments: list[TransactionChainPayment] = Field(default_factory=list)
    settlements: list[TransactionChainSettlement] = Field(default_factory=list)
    invoice: TransactionChainInvoice | None = None
    adjustments: list[TransactionChainAdjustment] = Field(default_factory=list)


class CaseDetailResponse(BaseModel):
    """Detailed case response including policy reasoning and full transaction chain."""

    case_id: str
    order_id: str
    decision: str
    exception_type: str
    priority: str
    financial_impact: float
    match_method: str
    match_confidence: float
    reason: str
    explanation: str
    next_action: str
    requires_ai: bool
    requires_human: bool
    payment_ids: list[str] = Field(default_factory=list)
    settlement_ids: list[str] = Field(default_factory=list)
    invoice_id: str | None = None
    adjustment_ids: list[str] = Field(default_factory=list)
    transaction_chain: TransactionChain | None = None
    created_at: str


class EvidenceResponse(BaseModel):
    """Deterministic match evidence and discrepancy explanations for a case."""

    case_id: str
    order_id: str
    match_method: str
    match_confidence: float
    evidence: dict[str, Any] = Field(default_factory=dict)
    reason: str
    explanation: str
    match_status: str
    match_discrepancy_reason: str = ""

