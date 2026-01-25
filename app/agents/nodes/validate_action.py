"""
Action Validation Node - Validates proposed actions with observability.
"""
from app.agents.state import AlertTriageState, create_event
from app.agents.llm import get_llm, MetricsTracker


async def validate_action(state: AlertTriageState) -> dict:
    """Validate the proposed remediation action."""
    action = state.get("recommended_action", "No action")
    service = state.get("alert", {}).get("service", "unknown")
    severity = state.get("alert", {}).get("severity", "unknown")
    triage_id = str(state.get("triage_id", "unknown"))
    
    with MetricsTracker(triage_id, "validate_action") as tracker:
        try:
            llm = get_llm()
            
            prompt = f"""Validate this action for {service} ({severity}):
Action: {action}

Is this:
- Safe? (yes/no + reason)
- Requires approval? (yes/no)"""

            response = llm.invoke(prompt)
            llm_reasoning = response.content if hasattr(response, 'content') else str(response)
            tracker.track_tokens(prompt, llm_reasoning)
            
            requires_approval = "yes" in llm_reasoning.lower() and "requires approval" in llm_reasoning.lower()
            
        except Exception as e:
            llm_reasoning = f"LLM unavailable: {e}"
            requires_approval = severity in ["critical", "medium", "high"]
    
    return {
        "requires_approval": requires_approval,
        "events": [create_event("validate_action", f"Validation complete. Requires approval: {requires_approval}", llm_reasoning=llm_reasoning)],
    }
