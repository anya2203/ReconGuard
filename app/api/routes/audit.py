"""Audit Trail & Financial Control Evidence API routes."""

from fastapi import APIRouter, HTTPException, Query

from app.api.schemas.audit import AuditEventResponse, CaseAuditTrailResponse
from app.services.reconciliation_service import ReconciliationService

router = APIRouter(prefix="/api/audit", tags=["Audit Trail"])


@router.get("/{case_id}", response_model=CaseAuditTrailResponse)
def get_case_audit_trail(case_id: str):
    """Retrieve chronological immutable audit trail for a specific reconciliation case."""
    service = ReconciliationService.get_instance()
    trail = service.get_audit_trail(case_id)
    if not trail:
        raise HTTPException(status_code=404, detail=f"Audit trail for case '{case_id}' not found.")
    return trail


@router.get("", response_model=list[AuditEventResponse])
def get_recent_audit_logs(limit: int = Query(50, ge=1, le=200, description="Maximum audit events to return")):
    """Retrieve recent system audit logs across all cases (read-only)."""
    service = ReconciliationService.get_instance()
    return service.get_all_audit_logs(limit=limit)

