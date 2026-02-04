"""
Metrics Analysis Node - Analyzes alert metrics with observability.

Uses tools:
- get_service_metrics: Query service-level metrics from Prometheus
- get_dcgm_metrics: Get current GPU health metrics
- get_dcgm_history: Get GPU metric trends for anomaly detection
- query_prometheus: Execute custom PromQL queries
"""
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AlertTriageState, create_event
from app.agents.llm import get_llm, MetricsTracker
from app.agents.tools.prometheus import get_service_metrics

# NVIDIA DCGM tools for GPU monitoring
from app.agents.tools.dcgm import get_dcgm_metrics, get_dcgm_history

# Prometheus MCP tools for custom queries
from app.mcp.prometheus import query_prometheus


async def analyze_metrics(state: AlertTriageState) -> dict:
    """
    Agentic Metrics Node.
    
    Uses tools to:
    - Query service metrics via get_service_metrics
    - Get GPU health via DCGM tools (for GPU-related alerts)
    - Execute custom PromQL queries for deep analysis
    """
    alert = state["alert"]
    service = alert.get("service", "unknown")
    triage_id = str(state.get("triage_id", "unknown"))
    
    with MetricsTracker(triage_id, "analyze_metrics") as tracker:
        try:
            # Bind all metrics-analysis relevant tools
            tools = [get_service_metrics, get_dcgm_metrics, get_dcgm_history, query_prometheus]
            llm = get_llm().bind_tools(tools)
            
            # Prepare context
            system_prompt = SystemMessage(content=f"""You are an NVIDIA Cluster Observability Agent.
Your job is to analyze metrics for the service '{service}'.
NVIDIA uses a pull-based Prometheus system (15s scrape interval) collecting DCGM metrics.

**Key DCGM Metrics to Monitor:**
- `dcgm_gpu_ecc_errors_total` (Check for rate > 0)
- `dcgm_gpu_temp` (Check for spikes > 80C)
- `dcgm_memory_bandwidth` (Utilization anomalies)

If you detect anomalies, always provide **copy-paste commands** for the SRE.

---
**Example Input:** Alert: GPU memory ECC errors on gpu-node-47

**Example Output:**
**Diagnosis:**
ECC errors are increasing on GPU 2. This indicates potential hardware degradation.

**Recommended SRE Commands:**
```bash
# Query Prometheus for current ECC error rate:
curl -G 'http://prometheus:9090/api/v1/query' \\
  --data-urlencode 'query=rate(dcgm_gpu_ecc_errors_total{{node="gpu-node-47"}}[5m])'

# Check GPU health on the node:
kubectl exec -it $(kubectl get pods -l app=dcgm-exporter -o name | head -1) -- nvidia-smi -q -d MEMORY,ECC

# View recent pod events on affected node:
kubectl get events --field-selector involvedObject.name=gpu-node-47 --sort-by=.lastTimestamp
```
---
If you don't have enough data, use the 'get_service_metrics' tool.
Look for CPU spikes, memory leaks, GPU thermal throttling, or ECC error increases.""")
            
            # Always append a clear instruction to the history
            prompt = f"Analyze metrics for {service}. Alert details: {alert}" if not state.get("messages") else f"Now, analyze the metrics for {service} to identify any anomalies."
            messages = [system_prompt] + state.get("messages", []) + [HumanMessage(content=prompt)]

            response = llm.invoke(messages)
            tracker.track_tokens(str(messages), response.content)
            
            # Record tool calls for observability
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for _ in response.tool_calls:
                    tracker.track_tool_call()
            
            # If the LLM didn't call a tool, we can summarize
            if not response.tool_calls:
                summary = response.content[:2000] if response.content else "Metrics analysis completed. See trace for details."
                return {
                    "metrics_summary": summary,
                    "messages": [response],
                    "events": [create_event("analyze_metrics", "Completed metrics analysis", llm_reasoning=response.content)],
                }
            else:
                # LLM wants to call a tool. Graph logic will handle the ToolNode.
                return {
                    "messages": [response],
                    "events": [create_event("analyze_metrics", f"Requesting metrics via tool: {response.tool_calls[0]['name']}", tool_calls=response.tool_calls)],
                }
            
        except Exception as e:
            error_msg = f"Metrics analysis failed: {str(e)}"
            return {
                "metrics_summary": "Error fetching metrics",
                "events": [create_event("analyze_metrics", "Failed to analyze metrics", error=error_msg)],
            }
