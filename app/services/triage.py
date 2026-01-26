"""
Triage queue service using asyncio.Queue with observability tracking.

In production this would be Kafka; for the MVP I use asyncio.Queue 
but kept the design event-driven.
"""
import asyncio
from datetime import datetime
from uuid import UUID

from app.models.alert import AlertPayload, TriageResult
from app.config import settings


# In-memory queue for MVP (Kafka-ready design)
triage_queue: asyncio.Queue[tuple[UUID, AlertPayload]] = asyncio.Queue()

# In-memory storage for triage results (will be replaced by Postgres)
triage_results: dict[UUID, TriageResult] = {}


async def enqueue_alert(triage_id: UUID, alert: AlertPayload) -> None:
    """
    Enqueue an alert for triage processing.
    
    In production, this would publish to a Kafka topic.
    """
    await triage_queue.put((triage_id, alert))
    print(f"📥 Alert {alert.id} queued for triage (triage_id: {triage_id})")


async def triage_worker() -> None:
    """
    Background worker that processes alerts from the queue.
    
    Runs continuously, pulling alerts and invoking the LangGraph workflow.
    Captures observability metrics for each triage session.
    """
    # Import here to avoid circular imports
    from app.agents.graph import run_triage_workflow
    from app.agents.observability import start_triage_metrics, end_triage_metrics
    
    print("🔄 Triage worker ready and waiting for alerts...")
    
    while True:
        try:
            # Wait for next alert
            triage_id, alert = await triage_queue.get()
            print(f"⚙️ Processing alert {alert.id} (triage_id: {triage_id})")
            
            # Start observability tracking
            start_triage_metrics(
                triage_id=str(triage_id),
                alert_id=str(alert.id),
                service=alert.service
            )
            
            try:
                # Run the LangGraph workflow
                result = await run_triage_workflow(triage_id, alert)
                
                # Store result (in production, write to Postgres)
                triage_results[triage_id] = result
                
                # End observability tracking
                end_triage_metrics(str(triage_id))
                
                print(f"✅ Triage complete for {alert.id}")
                print(f"   → Action: {result.recommended_action}")
                print(f"   → Confidence: {result.confidence:.2%}")
                print(f"   → Requires approval: {result.requires_approval}")
                
            except Exception as e:
                print(f"❌ Triage failed for {alert.id}: {e}")
                end_triage_metrics(str(triage_id))
                
                # Store failed result
                triage_results[triage_id] = TriageResult(
                    triage_id=triage_id,
                    alert_id=alert.id,
                    service=alert.service,
                    severity=alert.severity,
                    status="rejected",  # Use 'rejected' instead of 'failed'
                    events=[{
                        "node": "error",
                        "summary": str(e),
                        "ts": datetime.utcnow().isoformat(),
                    }],
                )
            
            triage_queue.task_done()
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ Worker error: {e}")


async def approve_triage(triage_id: UUID) -> TriageResult | None:
    """
    Approve a pending triage and resume the workflow.
    """
    from app.agents.graph import approve_triage_workflow
    
    if triage_id not in triage_results:
        return None
        
    print(f"👍 Approving triage session {triage_id}...")
    
    try:
        # Resume the LangGraph workflow
        result = await approve_triage_workflow(triage_id)
        
        # Store the updated result
        triage_results[triage_id] = result
        return result
        
    except Exception as e:
        print(f"❌ Approval failed for {triage_id}: {e}")
        return None


def get_triage_result(triage_id: UUID) -> TriageResult | None:
    """Get triage result by ID."""
    return triage_results.get(triage_id)


def get_all_triage_results() -> list[TriageResult]:
    """Get all triage results (for Streamlit dashboard)."""
    # Sort by completed_at or just chronological
    results = list(triage_results.values())
    return sorted(results, key=lambda x: x.triage_id.time if hasattr(x.triage_id, 'time') else 0, reverse=True)
