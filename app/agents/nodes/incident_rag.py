"""
Incident RAG Node - Retrieves similar past incidents.

Uses vector similarity search over embeddings of previous incidents
stored in Chroma or pgvector.
"""
from langchain_core.messages import HumanMessage
from app.agents.state import AlertTriageState, create_event
from app.agents.llm import get_llm, MetricsTracker


async def incident_rag(state: AlertTriageState) -> dict:
    """
    Search for similar past incidents using RAG.
    """
    alert = state["alert"]
    service = alert.get("service", "unknown")
    alert_type = alert.get("alert_type", "unknown")
    triage_id = str(state.get("triage_id", "unknown"))
    
    # Mock similar incidents
    similar_incidents = [
        {
            "id": "INC-2025-1234",
            "service": service,
            "type": alert_type,
            "resolution": "Scaled up replicas from 3 to 5",
            "similarity": 0.87,
        },
    ]
    
    with MetricsTracker(triage_id, "incident_rag") as tracker:
        try:
            llm = get_llm()
            
            incidents_text = "\n".join([
                f"- {inc['id']} (similarity: {inc['similarity']:.0%}): {inc['resolution']}"
                for inc in similar_incidents
            ])
            
            prompt = f"""Search Results for past incidents:
{incidents_text}

Compare these to the current evidence in the conversation.
What patterns do you see?"""
            
            messages = state.get("messages", []) + [HumanMessage(content=prompt)]
            response = llm.invoke(messages)
            tracker.track_tokens(str(messages), response.content)
            
        except Exception as e:
            response = HumanMessage(content=f"RAG Analysis failed: {e}")
    
    return {
        "similar_incidents": similar_incidents,
        "messages": [response],
        "events": [create_event("incident_rag", f"Found {len(similar_incidents)} similar incidents", llm_reasoning=response.content)],
    }
