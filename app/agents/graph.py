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


# Define the workflow graph
triage_graph = StateGraph(AlertTriageState)

# Add nodes
triage_graph.add_node("gather_context", gather_context)
triage_graph.add_node("analyze_logs", analyze_logs)
triage_graph.add_node("analyze_metrics", analyze_metrics)
triage_graph.add_node("incident_rag", incident_rag)
triage_graph.add_node("plan_remediation", plan_remediation)
triage_graph.add_node("validate_action", validate_action)
triage_graph.add_node("finalize", finalize)

# Define edges (linear flow for MVP)
triage_graph.set_entry_point("gather_context")
triage_graph.add_edge("gather_context", "analyze_logs")
triage_graph.add_edge("analyze_logs", "analyze_metrics")
triage_graph.add_edge("analyze_metrics", "incident_rag")
triage_graph.add_edge("incident_rag", "plan_remediation")
triage_graph.add_edge("plan_remediation", "validate_action")
triage_graph.add_edge("validate_action", "finalize")
triage_graph.add_edge("finalize", END)

# Compile the graph
triage_graph = triage_graph.compile()


async def run_triage_workflow(triage_id: UUID, alert: AlertPayload) -> TriageResult:
    """
    Run the triage workflow for an alert.
    
    Args:
        triage_id: Unique ID for this triage request
        alert: The alert payload to triage
    
    Returns:
        TriageResult with agent findings and recommendations
    """
    # Initialize state with triage_id
    initial_state: AlertTriageState = {
        "alert": alert.model_dump(mode="json"),
        "triage_id": str(triage_id),  # CRITICAL: Add triage_id so nodes can track metrics
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
    
    # Run the graph
    final_state = await triage_graph.ainvoke(initial_state)
    
    # Convert to TriageResult
    return TriageResult(
        triage_id=triage_id,
        alert_id=alert.id,
        service=alert.service,
        severity=alert.severity,
        status="pending" if final_state.get("requires_approval") else "approved",
        hypothesis=final_state.get("hypothesis", "Unknown"),
        recommended_action=final_state.get("recommended_action", "Manual investigation required"),
        confidence=final_state.get("confidence", 0.0),
        requires_approval=final_state.get("requires_approval", True),
        events=final_state.get("events", []),
    )
