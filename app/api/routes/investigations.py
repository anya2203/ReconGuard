"""AI Investigation routes."""

from fastapi import APIRouter, HTTPException
from app.api.schemas.investigations import (
    InvestigationListResponse,
    InvestigationRequest,
    InvestigationResponse,
)
from app.services.reconciliation_service import ReconciliationService

router = APIRouter(tags=["Investigations"])


@router.get("/api/investigations", response_model=InvestigationListResponse)
def list_investigations():
    """Retrieve all historical AI investigation findings."""
    service = ReconciliationService.get_instance()
    results = service.get_investigations()
    return {"total": len(results), "investigations": results}


@router.get("/api/investigations/{case_id}", response_model=InvestigationResponse)
def get_investigation_detail(case_id: str):
    """Retrieve detailed investigation result and tool execution trace for a case."""
    service = ReconciliationService.get_instance()
    investigation = service.get_investigation(case_id)
    if not investigation:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation for case '{case_id}' not found or not yet executed.",
        )
    return investigation


@router.post("/api/cases/{case_id}/investigate", response_model=InvestigationResponse)
def run_case_investigation(case_id: str, request: InvestigationRequest | None = None):
    """Execute read-only AI investigation on an eligible case."""
    service = ReconciliationService.get_instance()
    provider_name = request.provider if request else "mock"
    try:
        return service.investigate_case(case_id, provider_name=provider_name)
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=404, detail=err_msg)
        else:
            raise HTTPException(status_code=400, detail=err_msg)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Investigation error: {str(e)}",
        )

