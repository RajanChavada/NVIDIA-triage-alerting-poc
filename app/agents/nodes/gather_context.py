"""
Gather Context Node - Initial node that fetches logs and metrics.
"""
from app.agents.state import AlertTriageState, create_event


async def gather_context(state: AlertTriageState) -> dict:
    """
    Initial node that gathers context for the alert.
    
    - Fetches recent logs from the service
    - Retrieves metrics window around the alert timestamp
    - Sets up initial state for downstream agents
    """
    alert = state["alert"]
    service = alert.get("service", "unknown")
    timestamp = alert.get("timestamp", "")
    
    # TODO: Call actual log/metrics tools
    # For now, return placeholder data
    
    event = create_event(
        node="gather_context",
        summary=f"Gathered context for {service} alert at {timestamp}",
        service=service,
        logs_fetched=10,  # placeholder
        metrics_window="5m",  # placeholder
    )
    
    return {
        "events": [event],
    }
