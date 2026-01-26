"""
Alert triage API routes.

POST /alerts/triage - Receives alert payload, stores in DB, queues for processing.
GET /alerts/triage/{triage_id} - Get triage result by ID.
GET /alerts/triage - List all triage results.
"""
from uuid import uuid4, UUID

from fastapi import APIRouter, HTTPException, status

from app.models.alert import AlertPayload, TriageResponse, TriageResult
from app.services.triage import enqueue_alert, get_triage_result, get_all_triage_results


router = APIRouter()


@router.post("/triage", response_model=TriageResponse, status_code=status.HTTP_202_ACCEPTED)
async def triage_alert(alert: AlertPayload) -> TriageResponse:
    """
    Receive an alert and queue it for triage.
    
    1. Validates the alert payload
    2. Stores in PostgreSQL (TODO: implement DB persistence)
    3. Queues LangGraph workflow asynchronously
    4. Returns {"triage_id": uuid, "status": "queued"}
    """
    # Generate triage ID
    triage_id = uuid4()
    
    # TODO: Store alert in PostgreSQL
    # async with get_db() as db:
    #     db_alert = AlertRecord(**alert.model_dump())
    #     db.add(db_alert)
    #     await db.commit()
    
    # Queue for async processing
    await enqueue_alert(triage_id, alert)
    
    return TriageResponse(
        triage_id=triage_id,
        status="queued",
        message=f"Alert from {alert.service} ({alert.severity}) queued for triage",
    )


@router.get("/triage/{triage_id}", response_model=TriageResult)
async def get_triage_status(triage_id: UUID) -> TriageResult:
    """Get the status and result of a triage request."""
    result = get_triage_result(triage_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Triage {triage_id} not found",
        )
    
    return result


@router.get("/triage", response_model=list[TriageResult])
async def list_triage_results() -> list[TriageResult]:
    """List all triage results (for Streamlit dashboard)."""
    return get_all_triage_results()


@router.post("/triage/{triage_id}/approve")
async def approve_action(triage_id: UUID) -> dict:
    """
    Approve a recommended action and resume the triage workflow.
    """
    from app.services.triage import approve_triage
    
    result = await approve_triage(triage_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Triage {triage_id} not found or approval failed",
        )
    
    return {
        "triage_id": str(triage_id),
        "status": result.status,
        "action": result.recommended_action,
        "message": f"Action approved and executed for {result.service}",
    }


@router.post("/triage/{triage_id}/reject")
async def reject_action(triage_id: UUID, reason: str = "User rejected") -> dict:
    """
    Reject a recommended action.
    
    This feedback is valuable for training and will be sent to Langfuse.
    """
    result = get_triage_result(triage_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Triage {triage_id} not found",
        )
    
    # Update status
    result.status = "rejected"
    
    # TODO: Send negative feedback to Langfuse for evaluation
    
    return {
        "triage_id": str(triage_id),
        "status": "rejected",
        "reason": reason,
    }

@router.post("/generate", response_model=TriageResponse, status_code=status.HTTP_201_CREATED)
async def generate_and_triage(
    service_name: str | None = None,
    alert_type: str | None = None
) -> TriageResponse:
    """
    Generate a synthetic alert and automatically queue it for triage.
    
    This is used for demo purposes to avoid external alert triggers.
    """
    from app.services.alert_gen import generate_synthetic_alert
    
    # 1. Generate alert
    alert = generate_synthetic_alert(service_name, alert_type)
    
    # 2. Queue for triage
    triage_id = uuid4()
    await enqueue_alert(triage_id, alert)
    
    return TriageResponse(
        triage_id=triage_id,
        status="queued",
        message=f"Synthetic {alert.alert_type} alert for {alert.service} generated and queued.",
    )
