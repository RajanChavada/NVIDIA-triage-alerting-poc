"""
Remediation Planning Node - AI-powered action recommendations with observability.
"""
from app.agents.state import AlertTriageState, create_event
from app.agents.llm import get_llm, MetricsTracker


async def plan_remediation(state: AlertTriageState) -> dict:
    """Generate remediation plan based on analysis."""
    alert = state["alert"]
    service = alert.get("service", "unknown")
    logs_summary = state.get("logs_summary", "No log analysis available")
    metrics_summary = state.get("metrics_summary", "No metrics analysis")
    past_incidents = state.get("past_incidents", [])
    triage_id = str(state.get("triage_id", "unknown"))
    
    with MetricsTracker(triage_id, "plan_remediation") as tracker:
        try:
            llm = get_llm()
            
            prompt = f"""Based on this analysis for {service}:

Logs: {logs_summary}
Metrics: {metrics_summary}
Past Incidents: {len(past_incidents)} similar cases

Propose:
**Hypothesis:** Root cause in 1 sentence
**Action:** Specific remediation step
**Confidence:** 0-100%"""

            response = llm.invoke(prompt)
            llm_reasoning = response.content if hasattr(response, 'content') else str(response)
            tracker.track_tokens(prompt, llm_reasoning)
            
            # Parse response
            lines = llm_reasoning.split('\n')
            hypothesis = next((l.split(':', 1)[1].strip() for l in lines if 'hypothesis' in l.lower()), "Unknown")
            action = next((l.split(':', 1)[1].strip() for l in lines if 'action' in l.lower()), "Investigate")
            confidence = 75
            
        except Exception as e:
            llm_reasoning = f"LLM unavailable: {e}"
            hypothesis = "Service degradation"
            action = f"Scale {service}"
            confidence = 50
    
    return {
        "hypothesis": hypothesis,
        "recommended_action": action,
        "confidence": confidence / 100,
        "events": [create_event("plan_remediation", f"Proposed: {action[:100]} (confidence: {confidence}%)", llm_reasoning=llm_reasoning)],
    }
