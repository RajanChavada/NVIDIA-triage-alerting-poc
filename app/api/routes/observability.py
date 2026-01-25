"""
Observability API Routes - Metrics endpoints for monitoring.
"""
from fastapi import APIRouter
from typing import List
from app.agents.observability import get_all_metrics, get_triage_metrics

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/metrics")
async def get_metrics():
    """Get all triage metrics for observability dashboard."""
    metrics = get_all_metrics()
    return [m.to_dict() for m in metrics]


@router.get("/metrics/{triage_id}")
async def get_metrics_by_id(triage_id: str):
    """Get metrics for a specific triage session."""
    metrics = get_triage_metrics(triage_id)
    if metrics:
        return metrics.to_dict()
    return {"error": "Metrics not found"}
