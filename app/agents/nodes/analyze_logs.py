"""
Log Analysis Node - Analyzes logs for error patterns with metrics tracking.
"""
from app.agents.state import AlertTriageState, create_event
from app.agents.llm import get_llm, MetricsTracker


async def analyze_logs(state: AlertTriageState) -> dict:
    """Analyze logs for error patterns and anomalies."""
    from app.config import settings
    
    alert = state["alert"]
    service = alert.get("service", "unknown")
    context = alert.get("context", {})
    log_ids = context.get("recent_log_ids", [])
    alert_type = alert.get("alert_type", "unknown")
    severity = alert.get("severity", "unknown")
    triage_id = str(state.get("triage_id", "unknown"))
    
    # Track metrics
    with MetricsTracker(triage_id, "analyze_logs") as tracker:
        try:
            llm = get_llm(trace_name=f"analyze_logs_{service}")
            
            prompt = f"""You are a DevOps engineer analyzing logs for a {severity} severity {alert_type} alert in the {service} service.

Recent log IDs: {', '.join(log_ids)}

Analyze these logs and provide:
1. **Error Patterns**: What repeated errors do you see?
2. **Root Cause Hypothesis**: What might be causing this?
3. **Deployment Correlation**: Any recent changes that could explain this?"""

            response = llm.invoke(prompt)
            llm_reasoning = response.content if hasattr(response, 'content') else str(response)
            tracker.track_tokens(prompt, llm_reasoning)
            logs_summary = llm_reasoning[:200] + "..." if len(llm_reasoning) > 200 else llm_reasoning
            
        except Exception as e:
            llm_reasoning = f"LLM unavailable: {e}"
            logs_summary = f"Analyzed {len(log_ids)} logs for {service}"
    
    return {
        "logs_summary": logs_summary,
        "events": [create_event("analyze_logs", logs_summary, llm_reasoning=llm_reasoning)],
    }
