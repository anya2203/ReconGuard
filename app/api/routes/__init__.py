"""API Routes package initialization."""

from app.api.routes.cases import router as cases_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health import router as health_router
from app.api.routes.investigations import router as investigations_router

__all__ = [
    "health_router",
    "dashboard_router",
    "cases_router",
    "investigations_router",
]

