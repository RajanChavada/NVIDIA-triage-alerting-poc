"""
Finalize Node - Writes outcome to database and completes workflow.
"""
from datetime import datetime

from app.agents.state import AlertTriageState, create_event


async def finalize(state: AlertTriageState) -> dict:
    """
    Finalize the triage workflow.
    
    - Writes result to Postgres (TODO)
    - Updates alert status
    - Logs completion event
    """
    alert = state["alert"]
    service = alert.get("service", "unknown")
    
    recommended_action = state.get("recommended_action", "none")
    confidence = state.get("confidence", 0.0)
    requires_approval = state.get("requires_approval", True)
    
    status = "pending_approval" if requires_approval else "auto_approved"
    
    event = create_event(
        node="finalize",
        summary=f"Triage complete for {service}. Status: {status}",
        status=status,
        action=recommended_action,
        confidence=confidence,
    )
    
    # TODO: Write to Postgres
    # async with get_db() as db:
    #     result = TriageResultRecord(...)
    #     db.add(result)
    #     await db.commit()
    
    return {
        "events": [event],
    }
