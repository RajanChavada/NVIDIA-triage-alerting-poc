"""
Log Analysis Node - Analyzes logs for error patterns with metrics tracking.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AlertTriageState, create_event
from app.agents.llm import get_llm, MetricsTracker
from app.agents.tools.elasticsearch import search_logs


async def analyze_logs(state: AlertTriageState) -> dict:
    """
    Agentic Log Analysis Node.
    Uses search_logs tool to fetch data if needed, otherwise summarizes.
    """
    alert = state["alert"]
    service = alert.get("service", "unknown")
    triage_id = str(state.get("triage_id", "unknown"))
    
    with MetricsTracker(triage_id, "analyze_logs") as tracker:
        try:
            llm = get_llm().bind_tools([search_logs])
            
            # Prepare context
            system_prompt = SystemMessage(content=f"""You are an NVIDIA Cluster SRE Agent.
Your job is to analyze logs for the service '{service}'.
If you don't have enough information from the initial alert, use the 'search_logs' tool.
Look for stack traces, segmentation faults, or connection errors.""")
            
            # Always append a clear instruction to the history
            prompt = f"Analyze logs for {service}. Alert details: {alert}" if not state.get("messages") else f"Based on the investigation so far, analyze the logs for {service} to find the root cause."
            messages = [system_prompt] + state.get("messages", []) + [HumanMessage(content=prompt)]

            response = llm.invoke(messages)
            tracker.track_tokens(str(messages), response.content)
            
            # If the LLM didn't call a tool, we can summarize
            if not response.tool_calls:
                summary = response.content[:2000] if response.content else "Log analysis completed. See trace for details."
                return {
                    "logs_summary": summary,
                    "messages": [response],
                    "events": [create_event("analyze_logs", "Completed log analysis", llm_reasoning=response.content)],
                }
            else:
                # LLM wants to call a tool. Graph logic will handle the ToolNode.
                return {
                    "messages": [response],
                    "events": [create_event("analyze_logs", f"Searching logs via tool: {response.tool_calls[0]['name']}", tool_calls=response.tool_calls)],
                }
            
        except Exception as e:
            error_msg = f"Log analysis failed: {str(e)}"
            return {
                "logs_summary": "Error analyzing logs",
                "events": [create_event("analyze_logs", "Failed to analyze logs", error=error_msg)],
            }
