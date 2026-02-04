"""
Log Analysis Node - Analyzes logs for error patterns with metrics tracking.

Uses tools:
- search_logs: Query Elasticsearch for log patterns
- get_recent_messages: Check Kafka for correlated events
- query_prometheus: Check if related alert rules fired
"""
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AlertTriageState, create_event
from app.agents.llm import get_llm, MetricsTracker
from app.agents.tools.elasticsearch import search_logs

# MCP Tools for log correlation
from app.mcp.kafka import get_recent_messages
from app.mcp.prometheus import query_prometheus, get_alert_rules


async def analyze_logs(state: AlertTriageState) -> dict:
    """
    Agentic Log Analysis Node.
    
    Uses tools to:
    - Search Elasticsearch for error patterns
    - Check Kafka for correlated events from other services
    - Query Prometheus for related alert activity
    """
    alert = state["alert"]
    service = alert.get("service", "unknown")
    triage_id = str(state.get("triage_id", "unknown"))
    
    with MetricsTracker(triage_id, "analyze_logs") as tracker:
        try:
            # Bind all log-analysis relevant tools
            tools = [search_logs, get_recent_messages, query_prometheus, get_alert_rules]
            llm = get_llm().bind_tools(tools)
            
            # Prepare context
            system_prompt = SystemMessage(content=f"""You are an NVIDIA Cluster SRE Agent.
Your job is to analyze logs for the service '{service}'.
Use diagnostic patterns from ChatOps (e.g., `/sre diagnose`).

**Key Log Patterns to Identify:**
- DCGM health check failures
- `nvidia-smi` output anomalies (XID errors)
- Stack traces, segmentation faults, or GPU driver ECC errors

If you find issues, always provide **copy-paste commands** for the SRE.

---
**Example Input:** Alert: GPU driver errors on gpu-node-47

**Example Output:**
**Log Analysis:**
Found 'XID 79: GPU has fallen off the bus' in system logs. This is a critical hardware failure.

**Recommended SRE Commands:**
```bash
# Check GPU health directly on the node:
ssh bastion -t 'ssh gpu-node-47 nvidia-smi -q'

# Run DCGM diagnostics:
kubectl exec -it dcgm-exporter-xxxxx -- dcgmi health -c -g 0

# Search for XID errors in the last hour:
kubectl logs -l app=dcgm-exporter --since=1h | grep -i 'xid'

# View dmesg for GPU driver issues:
ssh bastion -t 'ssh gpu-node-47 dmesg | tail -50 | grep -i nvidia'
```
---
If you don't have enough information from the initial alert, use the 'search_logs' tool.""")
            
            # Always append a clear instruction to the history
            prompt = f"Analyze logs for {service}. Alert details: {alert}" if not state.get("messages") else f"Based on the investigation so far, analyze the logs for {service} to find the root cause."
            messages = [system_prompt] + state.get("messages", []) + [HumanMessage(content=prompt)]

            response = llm.invoke(messages)
            tracker.track_tokens(str(messages), response.content)
            
            # Record tool calls for observability
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for _ in response.tool_calls:
                    tracker.track_tool_call()
            
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
