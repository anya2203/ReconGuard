"""Dashboard summary and benchmark metrics routes."""

from fastapi import APIRouter
from app.api.schemas.dashboard import BenchmarkMetricsResponse, DashboardSummaryResponse
from app.services.reconciliation_service import ReconciliationService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary():
    """Retrieve high-level reconciliation KPIs, policy counts, and financial exposure."""
    service = ReconciliationService.get_instance()
    return service.get_dashboard_summary()


@router.get("/benchmark", response_model=BenchmarkMetricsResponse)
def get_benchmark_metrics():
    """Retrieve verified Phase 1 benchmark metrics and throughput telemetry."""
    service = ReconciliationService.get_instance()
    return service.get_benchmark_metrics()
