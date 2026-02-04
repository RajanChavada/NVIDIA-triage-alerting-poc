"""
Gather Context Node - Agentic node that fetches initial context using MCP tools.

Uses tools to gather:
- GPU inventory (DCGM) for GPU-related alerts
- Recent Kafka messages for correlated events
- Available Prometheus metrics
"""
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AlertTriageState, create_event
from app.agents.llm import get_llm, MetricsTracker

# MCP Tools for initial context gathering
from app.agents.tools.dcgm import list_dcgm_gpus
from app.mcp.kafka import get_recent_messages
from app.mcp.prometheus import list_metrics, get_alert_rules


async def gather_context(state: AlertTriageState) -> dict:
    """
    Agentic Context Gathering Node.
    
    Uses MCP tools to gather initial context:
    - For GPU alerts: lists available GPUs, checks recent GPU events
    - For service alerts: checks recent Kafka events, available metrics
    - Always: checks active alert rules to understand firing conditions
    """
    alert = state["alert"]
    service = alert.get("service", "unknown")
    alert_type = alert.get("alert_type", "unknown")
    timestamp = alert.get("timestamp", "")
    triage_id = str(state.get("triage_id", "unknown"))
    
    with MetricsTracker(triage_id, "gather_context") as tracker:
        try:
            # Bind context-gathering tools to the LLM
            tools = [list_dcgm_gpus, get_recent_messages, list_metrics, get_alert_rules]
            llm = get_llm().bind_tools(tools)
            
            system_prompt = SystemMessage(content=f"""You are an NVIDIA Cluster Context Agent.
Your job is to gather initial context for triaging an alert.

**Available Tools:**
- `list_dcgm_gpus`: List all GPUs in the cluster (use for GPU-related alerts)
- `get_recent_messages`: Get recent Kafka events (use to find correlated events)
- `list_metrics`: List available Prometheus metrics (use to understand what we can query)
- `get_alert_rules`: Get configured alert rules (use to understand alert thresholds)

**Strategy:**
- For GPU alerts (temperature, memory, ECC errors): Call `list_dcgm_gpus` first
- For service alerts (latency, error rate): Call `get_recent_messages` for topic "service-alerts"
- Always helpful: Call `get_alert_rules` to understand what triggered the alert

Gather the context needed for downstream analysis agents.""")

            prompt = f"""Gather context for this alert:
- Service: {service}
- Alert Type: {alert_type}
- Timestamp: {timestamp}
- Full Alert: {alert}

Call the appropriate tools to gather initial context."""

            messages = [system_prompt, HumanMessage(content=prompt)]
            response = llm.invoke(messages)
            tracker.track_tokens(str(messages), response.content)
            
            # Track tool calls for observability
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for _ in response.tool_calls:
                    tracker.track_tool_call()
                
                # LLM wants to call tools - graph will handle via ToolNode
                return {
                    "messages": [response],
                    "events": [create_event(
                        "gather_context",
                        f"Gathering context via tools: {[tc['name'] for tc in response.tool_calls]}",
                        tool_calls=response.tool_calls,
                        service=service,
                    )],
                }
            else:
                # LLM provided direct assessment without tools
                return {
                    "messages": [response],
                    "events": [create_event(
                        "gather_context",
                        f"Gathered context for {service} alert at {timestamp}",
                        llm_reasoning=response.content,
                        service=service,
                    )],
                }
                
        except Exception as e:
            error_msg = f"Context gathering failed: {str(e)}"
            return {
                "events": [create_event(
                    "gather_context",
                    "Failed to gather context",
                    error=error_msg,
                    service=service,
                )],
            }
