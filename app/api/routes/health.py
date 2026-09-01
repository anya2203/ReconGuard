"""Health check endpoint routes."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
@router.get("/api/health")
def health_check():
    """Health check endpoint confirming backend service operational status."""
    return {"status": "healthy", "service": "ReconGuard API"}

