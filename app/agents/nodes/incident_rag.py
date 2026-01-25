"""
Incident RAG Node - Retrieves similar past incidents.

Uses vector similarity search over embeddings of previous incidents
stored in Chroma or pgvector.
"""
from app.agents.state import AlertTriageState, create_event
from app.agents.llm import get_llm


async def incident_rag(state: AlertTriageState) -> dict:
    """
    Search for similar past incidents using RAG.
    
    - Embeds current alert context
    - Queries vector DB for similar incidents
    - Returns relevant remediation history
    """
    alert = state["alert"]
    service = alert.get("service", "unknown")
    alert_type = alert.get("alert_type", "unknown")
    anomalies = state.get("anomalies", [])
    
    # Mock similar incidents (in production: query vector DB)
    similar_incidents = [
        {
            "id": "INC-2025-1234",
            "service": service,
            "type": alert_type,
            "resolution": "Scaled up replicas from 3 to 5",
            "similarity": 0.87,
        },
        {
            "id": "INC-2025-1100",
            "service": service,
            "type": "latency_spike",
            "resolution": "Applied rate limiting to upstream",
            "similarity": 0.72,
        },
    ]
    
    # Use LLM to analyze similar incidents
    try:
        llm = get_llm()
        
        incidents_text = "\n".join([
            f"- {inc['id']} (similarity: {inc['similarity']:.0%}): {inc['resolution']}"
            for inc in similar_incidents
        ])
        
        prompt = f"""You are analyzing past incidents similar to the current {alert_type} alert in {service}.

**Current Alert Context:**
- Service: {service}
- Type: {alert_type}
- Anomalies: {', '.join(anomalies)}

**Similar Past Incidents:**
{incidents_text}

As a DevOps expert:
1. **Pattern Recognition**: What patterns do you see across these incidents?
2. **Best Resolution**: Which resolution is most applicable to the current situation?
3. **Lessons Learned**: What do these past incidents teach us?

Think step-by-step."""

        response = llm.invoke(prompt)
        llm_reasoning = response.content if hasattr(response, 'content') else str(response)
        
    except Exception as e:
        llm_reasoning = f"LLM unavailable: {e}. Using similarity scores only."
    
    event = create_event(
        node="incident_rag",
        summary=f"Found {len(similar_incidents)} similar past incidents",
        incidents_found=len(similar_incidents),
        top_similarity=0.87,
        llm_reasoning=llm_reasoning,
    )
    
    return {
        "similar_incidents": similar_incidents,
        "events": [event],
    }
