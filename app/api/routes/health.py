"""
Health check endpoints for liveness/readiness probes.
"""
from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check - verifies all dependencies are available.
    
    TODO: Add database connectivity check
    """
    return {
        "status": "ready",
        "llm_provider": settings.llm_provider,
        "langfuse_enabled": settings.langfuse_enabled,
    }
