"""Reconciliation cases and evidence routes."""

from fastapi import APIRouter, HTTPException, Query
from app.api.schemas.cases import CaseDetailResponse, CaseListResponse, EvidenceResponse, TransactionChain
from app.services.reconciliation_service import ReconciliationService

router = APIRouter(prefix="/api/cases", tags=["Cases"])


@router.get("", response_model=CaseListResponse)
def list_cases(
    page: int = Query(1, ge=1, description="Page number, 1-indexed"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    decision: str | None = Query(None, description="Filter by policy decision (AUTO_RESOLVE, AI_INVESTIGATION, HUMAN_REVIEW, ESCALATE)"),
    priority: str | None = Query(None, description="Filter by priority (HIGH, MEDIUM, LOW)"),
    exception_type: str | None = Query(None, description="Filter by exception category"),
    search: str | None = Query(None, description="Search by Case ID or Order ID"),
):
    """Query and paginate reconciliation cases with multi-criteria filtering."""
    service = ReconciliationService.get_instance()
    try:
        return service.get_cases(
            page=page,
            page_size=page_size,
            decision=decision,
            priority=priority,
            exception_type=exception_type,
            search=search,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case_detail(case_id: str):
    """Retrieve complete case details, policy rationale, and full multi-entity transaction chain."""
    service = ReconciliationService.get_instance()
    case = service.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    tx_chain_dict = service.get_transaction_chain(case_id)
    case_dict = case.to_dict()
    case_dict["transaction_chain"] = tx_chain_dict
    return case_dict


@router.get("/{case_id}/evidence", response_model=EvidenceResponse)
def get_case_evidence(case_id: str):
    """Retrieve deterministic evidence bundle and matching strategy discrepancy diagnosis."""
    service = ReconciliationService.get_instance()
    evidence = service.get_evidence(case_id)
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return evidence

