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


import json
import os
from pathlib import Path

# In-memory queue for MVP (Kafka-ready design)
triage_queue: asyncio.Queue[tuple[UUID, AlertPayload]] = asyncio.Queue()

# In-memory storage with file persistence for demo
CACHE_PATH = Path("data")
CACHE_PATH.mkdir(exist_ok=True)
CACHE_FILE = CACHE_PATH / "triage_results.json"

# In-memory storage for triage results
triage_results: dict[UUID, TriageResult] = {}

def save_cache():
    """Save triage results to local JSON file."""
    try:
        data = {str(k): v.model_dump(mode="json") for k, v in triage_results.items()}
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to save triage cache: {e}")

def load_cache():
    """Load triage results from local JSON file."""
    if not CACHE_FILE.exists():
        return
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
            for k, v in data.items():
                triage_results[UUID(k)] = TriageResult(**v)
        print(f"📜 Loaded {len(triage_results)} results from cache.")
    except Exception as e:
        print(f"⚠️ Failed to load triage cache: {e}")

# Initial load
load_cache()


async def enqueue_alert(triage_id: UUID, alert: AlertPayload) -> None:
    """
    Enqueue an alert for triage processing.
    """
    await triage_queue.put((triage_id, alert))
    print(f"📥 Alert {alert.id} queued for triage (triage_id: {triage_id})")


async def triage_worker() -> None:
    """
    Background worker that processes alerts from the queue.
    """
    from app.agents.graph import run_triage_workflow
    from app.agents.observability import start_triage_metrics, end_triage_metrics
    
    print("🔄 Triage worker ready and waiting for alerts...")
    
    while True:
        try:
            triage_id, alert = await triage_queue.get()
            
            start_triage_metrics(
                triage_id=str(triage_id),
                alert_id=str(alert.id),
                service=alert.service
            )
            
            try:
                result = await run_triage_workflow(triage_id, alert)
                triage_results[triage_id] = result
                save_cache() # Persist
                end_triage_metrics(str(triage_id))
                
            except Exception as e:
                print(f"❌ Triage failed for {alert.id}: {e}")
                end_triage_metrics(str(triage_id))
                
                triage_results[triage_id] = TriageResult(
                    triage_id=triage_id,
                    alert_id=alert.id,
                    service=alert.service,
                    severity=alert.severity,
                    status="rejected",
                    events=[{
                        "node": "error",
                        "summary": str(e),
                        "ts": datetime.utcnow().isoformat(),
                    }],
                )
                save_cache() # Persist
            
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
        
    try:
        result = await approve_triage_workflow(triage_id)
        triage_results[triage_id] = result
        save_cache() # Persist
        return result
    except Exception as e:
        print(f"❌ Approval failed for {triage_id}: {e}")
        return None


def get_triage_result(triage_id: UUID) -> TriageResult | None:
    """Get triage result by ID."""
    return triage_results.get(triage_id)


def get_all_triage_results() -> list[TriageResult]:
    """Get all triage results (for Streamlit dashboard)."""
    results = list(triage_results.values())
    # Sort by triage_id (roughly chronological for UUIDv4)
    return sorted(results, key=lambda x: str(x.triage_id), reverse=True)
