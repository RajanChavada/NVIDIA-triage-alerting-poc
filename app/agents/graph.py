"""
LangGraph workflow definition - Multi-agent triage system.

The workflow follows a DAG structure:
1. gather_context → 2. analyze_logs → 3. analyze_metrics → 4. incident_rag
→ 5. plan_remediation → 6. validate_action → 7. finalize
"""
from uuid import UUID

from langgraph.graph import StateGraph, END

from app.models.alert import AlertPayload, TriageResult
from app.agents.state import AlertTriageState

# Import all agent nodes
from app.agents.nodes.gather_context import gather_context
from app.agents.nodes.analyze_logs import analyze_logs
from app.agents.nodes.analyze_metrics import analyze_metrics
from app.agents.nodes.incident_rag import incident_rag
from app.agents.nodes.plan_remediation import plan_remediation
from app.agents.nodes.validate_action import validate_action
from app.agents.nodes.finalize import finalize

# Tool support
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphInterrupt
from app.agents.tools.prometheus import get_service_metrics
from app.agents.tools.elasticsearch import search_logs

# Define the tools
tools = [get_service_metrics, search_logs]
tool_node = ToolNode(tools)

# In-memory checkpointer (triage results are persisted to JSON by triage.py)
checkpointer = MemorySaver()

def should_continue(state: AlertTriageState):
    """Determine if we should continue to tools or move to next node."""
    messages = state.get("messages", [])
    if not messages:
        return "next"
    
    last_message = messages[-1]
    # If the LLM made a tool call, then we route to the "tools" node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    # Otherwise, we stop
    return "next"

# Define the workflow graph
triage_graph = StateGraph(AlertTriageState)

# Add nodes
triage_graph.add_node("gather_context", gather_context)
triage_graph.add_node("analyze_logs", analyze_logs)
triage_graph.add_node("analyze_metrics", analyze_metrics)
triage_graph.add_node("tools", tool_node)
triage_graph.add_node("incident_rag", incident_rag)
triage_graph.add_node("plan_remediation", plan_remediation)
triage_graph.add_node("validate_action", validate_action)
triage_graph.add_node("finalize", finalize)

# Define edges with tool loops
triage_graph.set_entry_point("gather_context")
triage_graph.add_edge("gather_context", "analyze_logs")

# Analyze Logs loop
triage_graph.add_conditional_edges(
    "analyze_logs",
    should_continue,
    {
        "tools": "tools",
        "next": "analyze_metrics",
    },
)

# Analyze Metrics loop
triage_graph.add_conditional_edges(
    "analyze_metrics",
    should_continue,
    {
        "tools": "tools",
        "next": "incident_rag",
    },
)

# Tool routing logic
def route_tool_output(state: AlertTriageState):
    messages = state.get("messages", [])
    if not messages: return "analyze_metrics"
    for msg in reversed(messages):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            tool_name = msg.tool_calls[0]["name"]
            if tool_name == "search_logs":
                return "analyze_logs"
            if tool_name == "get_service_metrics":
                return "analyze_metrics"
    return "analyze_metrics"

triage_graph.add_conditional_edges("tools", route_tool_output, {
    "analyze_logs": "analyze_logs",
    "analyze_metrics": "analyze_metrics"
})

triage_graph.add_edge("incident_rag", "plan_remediation")
triage_graph.add_edge("plan_remediation", "validate_action")
triage_graph.add_edge("validate_action", "finalize")
triage_graph.add_edge("finalize", END)

# Compile the graph with checkpointer and interrupt before finalize
triage_graph = triage_graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["finalize"]
)


async def run_triage_workflow(triage_id: UUID, alert: AlertPayload) -> TriageResult:
    """
    Run the triage workflow for an alert.
    """
    # Initialize state
    initial_state: AlertTriageState = {
        "alert": alert.model_dump(mode="json"),
        "triage_id": str(triage_id),
        "messages": [],
        "logs_summary": "",
        "metrics_summary": "",
        "anomalies": [],
        "similar_incidents": [],
        "hypothesis": "",
        "recommended_action": "",
        "confidence": 0.0,
        "requires_approval": True,
        "events": [],
    }
    
    # Run the graph with a thread_id for persistence
    config = {"configurable": {"thread_id": str(triage_id)}}
    
    # ainvoke will run until it hits the 'finalize' node (because interrupt_before=["finalize"])
    final_state = await triage_graph.ainvoke(initial_state, config=config)
    
    # If no approval is required, auto-resume to run 'finalize' and set completed_at
    if not final_state.get("requires_approval", True):
        print(f"⏩ No approval required for {triage_id}, auto-finalizing...")
        final_state = await triage_graph.ainvoke(None, config=config)
    
    # Convert state to TriageResult
    return TriageResult(
        triage_id=triage_id,
        alert_id=alert.id,
        service=alert.service,
        severity=alert.severity,
        status="pending" if final_state.get("requires_approval") else "approved",
        logs_summary=final_state.get("logs_summary") or "Investigation completed. See trace.",
        metrics_summary=final_state.get("metrics_summary") or "Metrics analyzed. See trace.",
        hypothesis=final_state.get("hypothesis") or "Analysis in progress...",
        recommended_action=final_state.get("recommended_action") or "Manual investigation required",
        confidence=final_state.get("confidence", 0.0),
        requires_approval=final_state.get("requires_approval", True),
        events=final_state.get("events", []),
        completed_at=final_state.get("completed_at"),
    )


async def approve_triage_workflow(triage_id: UUID) -> TriageResult:
    """
    Resume the workflow after human approval.
    """
    config = {"configurable": {"thread_id": str(triage_id)}}
    
    # Resume by passing None as input, it picks up where it left off
    final_state = await triage_graph.ainvoke(None, config=config)
    
    # The state should now have finished the 'finalize' node
    return TriageResult(
        triage_id=triage_id,
        alert_id=UUID(final_state["alert"]["id"]),
        service=final_state["alert"]["service"],
        severity=final_state["alert"]["severity"],
        status="approved",
        logs_summary=final_state.get("logs_summary") or "Investigation completed. See trace.",
        metrics_summary=final_state.get("metrics_summary") or "Metrics analyzed. See trace.",
        hypothesis=final_state.get("hypothesis") or "Analysis complete.",
        recommended_action=final_state.get("recommended_action") or "Action approved.",
        confidence=final_state.get("confidence", 1.0),
        requires_approval=False,
        events=final_state.get("events", []),
        completed_at=final_state.get("completed_at"),
    )
