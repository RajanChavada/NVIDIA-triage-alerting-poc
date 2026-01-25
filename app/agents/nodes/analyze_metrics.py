"""
Metrics Analysis Node - Analyzes alert metrics with observability.
"""
from app.agents.state import AlertTriageState, create_event
from app.agents.llm import get_llm, MetricsTracker


async def analyze_metrics(state: AlertTriageState) -> dict:
    """Analyze metrics and identify anomalies."""
    alert = state["alert"]
    service = alert.get("service", "unknown")
    metrics = alert.get("metrics", {})
    alert_type = alert.get("alert_type", "unknown")
    triage_id = str(state.get("triage_id", "unknown"))
    
    with MetricsTracker(triage_id, "analyze_metrics") as tracker:
        try:
            llm = get_llm()
            
            prompt = f"""Analyze these metrics for {service}:
{metrics}

Alert Type: {alert_type}

Provide:
1. Interpretation: What do these metrics tell us?
2. Severity Assessment: How urgent is this?  
3. Expected Behavior: What's normal for this service?"""

            response = llm.invoke(prompt)
            llm_reasoning = response.content if hasattr(response, 'content') else str(response)
            tracker.track_tokens(prompt, llm_reasoning)
            summary = llm_reasoning[:200] + "..." if len(llm_reasoning) > 200 else llm_reasoning
            
        except Exception as e:
            llm_reasoning = f"LLM unavailable: {e}"
            summary = f"Metrics analysis for {service}"
    
    return {
        "metrics_summary": summary,
        "events": [create_event("analyze_metrics", summary, llm_reasoning=llm_reasoning)],
    }
