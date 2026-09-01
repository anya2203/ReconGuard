"""Dashboard summary routes."""

from fastapi import APIRouter
from app.api.schemas.dashboard import DashboardSummaryResponse
from app.services.reconciliation_service import ReconciliationService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary():
    """Retrieve high-level reconciliation KPIs, policy counts, and financial exposure."""
    service = ReconciliationService.get_instance()
    return service.get_dashboard_summary()

