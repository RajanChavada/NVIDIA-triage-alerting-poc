"""
AlertTriageState - State definition for the LangGraph workflow.

Events are first-class citizens: every node appends an event dict
that powers the Streamlit trace visualization.
"""
from typing import Annotated, TypedDict
from operator import add

from langgraph.graph.message import add_messages


class AlertTriageState(TypedDict):
    """
    State passed through the LangGraph triage workflow.
    
    Attributes:
        triage_id: Unique ID for this triage session (for metrics tracking)
        alert: Original alert payload as dict
        messages: LangChain message history (for LLM context)
        logs_summary: Summary from log analysis agent
        metrics_summary: Summary from metrics analysis agent
        anomalies: List of detected anomalies
        similar_incidents: RAG results from incident KB
        hypothesis: Root cause hypothesis
        recommended_action: Proposed remediation action
        confidence: Agent confidence in recommendation (0.0-1.0)
        requires_approval: Whether human approval is needed
        events: Trace events for Streamlit UI (first-class citizen)
    """
    
    # Triage session ID (for metrics)
    triage_id: str
    
    # Input
    alert: dict
    
    # LLM message history
    messages: Annotated[list, add_messages]
    
    # Agent outputs
    logs_summary: str
    metrics_summary: str
    anomalies: list[str]
    similar_incidents: list[dict]
    
    # Decision
    hypothesis: str
    recommended_action: str
    confidence: float
    requires_approval: bool
    
    # Trace for UI - events accumulate using add operator
    events: Annotated[list[dict], add]


def create_event(node: str, summary: str, **extra) -> dict:
    """
    Create a trace event for the Streamlit UI.
    
    Every node should call this and add to events list.
    
    Args:
        node: Name of the current node
        summary: Brief description of what happened
        **extra: Additional metadata (e.g., tool outputs, confidence)
    
    Returns:
        Event dict with timestamp
    """
    from datetime import datetime
    
    return {
        "node": node,
        "summary": summary,
        "ts": datetime.utcnow().isoformat(),
        **extra,
    }
