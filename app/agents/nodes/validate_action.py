from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AlertTriageState, create_event
from app.agents.llm import get_llm, MetricsTracker


async def validate_action(state: AlertTriageState) -> dict:
    """Validate the proposed remediation action using context."""
    action = state.get("recommended_action", "No action")
    service = state.get("alert", {}).get("service", "unknown")
    severity = state.get("alert", {}).get("severity", "unknown")
    triage_id = str(state.get("triage_id", "unknown"))
    
    with MetricsTracker(triage_id, "validate_action") as tracker:
        try:
            llm = get_llm()
            
            system_prompt = SystemMessage(content=f"""You are an NVIDIA Cluster Security & Reliability Guardrail.
Assess the risk of the proposed action for {service}.
Consider if it's a destructive action (like deleting pods) or a safe one (like scaling).""")
            
            prompt = f"""Assess this plan:
Action: {action}
Severity: {severity}

Provide:
1. **Safety Assessment**: Is this action safe to execute?
2. **Approval Gateway**: Does this require human approval? (Answer 'YES' for high risk or uncertain actions, 'NO' otherwise)"""
            
            messages = [system_prompt] + state.get("messages", []) + [HumanMessage(content=prompt)]
            response = llm.invoke(messages)
            tracker.track_tokens(str(messages), response.content)
            
            llm_reasoning = response.content
            # Determine approval requirement
            requires_approval = "YES" in llm_reasoning.upper() or severity in ["critical", "high"]
            
        except Exception as e:
            llm_reasoning = f"Validation failed: {e}"
            requires_approval = True # Fail-safe: require approval
            response = HumanMessage(content=llm_reasoning)
    
    return {
        "requires_approval": requires_approval,
        "messages": [response],
        "events": [create_event("validate_action", f"Validation complete. Requires approval: {requires_approval}", llm_reasoning=llm_reasoning)],
    }
