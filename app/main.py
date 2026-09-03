"""ReconGuard FastAPI Application Entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    audit_router,
    cases_router,
    dashboard_router,
    health_router,
    investigations_router,
)
from app.database import Base, engine
import app.models

# Initialize DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ReconGuard API",
    description="Intelligent Payment Reconciliation & Exception Management Backend API",
    version="1.0.0",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(cases_router)
app.include_router(investigations_router)
app.include_router(audit_router)