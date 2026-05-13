"""
Health check endpoint.
"""
from datetime import datetime
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Liveness check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
