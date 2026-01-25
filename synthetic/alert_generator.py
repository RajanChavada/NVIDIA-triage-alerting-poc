"""
Alert Generator - End-to-end demo script.

This script:
1. Generates a fake alert
2. POSTs to /alerts/triage
3. Waits for processing
4. Reads back TriageResult and prints it

Run with: python -m synthetic.alert_generator
"""
import asyncio
import random
from datetime import datetime
from pathlib import Path

import httpx
import yaml


# Load service registry
SERVICES_FILE = Path(__file__).parent / "services.yaml"


def load_services() -> dict:
    """Load service registry from YAML."""
    with open(SERVICES_FILE) as f:
        return yaml.safe_load(f)


def generate_alert() -> dict:
    """
    Generate a realistic fake alert.
    
    Creates an alert with:
    - Random service from registry
    - Metrics with anomalous values
    - Appropriate severity based on deviation
    """
    config = load_services()
    services = config["services"]
    alert_types = config["alert_types"]
    detectors = config["detectors"]
    
    # Pick random service
    service = random.choice(services)
    service_name = service["name"]
    
    # Pick random alert type
    alert_type = random.choice(alert_types)
    
    # Generate metric snapshot with anomaly
    metric_snapshot = {}
    for metric in service.get("metrics", []):
        baseline = metric["baseline"]
        metric_name = metric["name"]
        
        # Create anomalous value (1.5x - 10x baseline)
        multiplier = random.uniform(1.5, 10.0)
        current_value = baseline * multiplier
        
        if "latency" in metric_name:
            metric_snapshot["latency_p95_ms"] = round(current_value, 1)
            metric_snapshot["latency_baseline_ms"] = baseline
        elif "error" in metric_name:
            metric_snapshot["error_rate"] = min(round(current_value, 3), 1.0)
            metric_snapshot["error_rate_baseline"] = baseline
        elif "cpu" in metric_name:
            metric_snapshot["cpu_percent"] = min(round(current_value, 1), 100)
            metric_snapshot["cpu_baseline"] = baseline
        elif "memory" in metric_name:
            metric_snapshot["memory_percent"] = min(round(current_value, 1), 100)
            metric_snapshot["memory_baseline"] = baseline
    
    # Determine severity based on criticality and deviation
    if service.get("criticality") == "critical":
        severity = "critical" if random.random() > 0.3 else "high"
    elif service.get("criticality") == "high":
        severity = "high" if random.random() > 0.5 else "medium"
    else:
        severity = random.choice(["medium", "low"])
    
    return {
        "service": service_name,
        "severity": severity,
        "alert_type": alert_type,
        "detector": random.choice(detectors),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metric_snapshot": metric_snapshot,
        "context": {
            "recent_log_ids": [f"log-{random.randint(1000, 9999)}" for _ in range(3)],
            "region": service.get("region", "us-central1"),
        }
    }


async def send_alert(alert: dict, base_url: str = "http://localhost:8000") -> dict:
    """Send alert to triage API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/alerts/triage",
            json=alert,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


async def get_triage_result(triage_id: str, base_url: str = "http://localhost:8000") -> dict:
    """Poll for triage result."""
    async with httpx.AsyncClient() as client:
        for _ in range(10):  # Poll up to 10 times
            await asyncio.sleep(1)
            try:
                response = await client.get(
                    f"{base_url}/alerts/triage/{triage_id}",
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return response.json()
            except Exception:
                pass
        return None


async def main():
    """Run end-to-end demo."""
    print("=" * 60)
    print("🚨 NVIDIA Triage Alerting MVP - Demo")
    print("=" * 60)
    
    # Generate alert
    alert = generate_alert()
    print(f"\n📤 Generated Alert:")
    print(f"   Service: {alert['service']}")
    print(f"   Severity: {alert['severity']}")
    print(f"   Type: {alert['alert_type']}")
    print(f"   Detector: {alert['detector']}")
    print(f"   Metrics: {alert['metric_snapshot']}")
    
    # Send to API
    print(f"\n⏳ Sending to /alerts/triage...")
    try:
        result = await send_alert(alert)
        triage_id = result["triage_id"]
        print(f"   ✅ Queued! Triage ID: {triage_id}")
    except Exception as e:
        print(f"   ❌ Failed to send alert: {e}")
        print(f"   Make sure the server is running: uvicorn app.main:app --reload")
        return
    
    # Wait for result
    print(f"\n⏳ Waiting for triage result...")
    triage_result = await get_triage_result(triage_id)
    
    if triage_result:
        print(f"\n✅ Triage Complete!")
        print(f"   Hypothesis: {triage_result.get('hypothesis', 'N/A')}")
        print(f"   Action: {triage_result.get('recommended_action', 'N/A')}")
        print(f"   Confidence: {triage_result.get('confidence', 0):.0%}")
        print(f"   Requires Approval: {triage_result.get('requires_approval', True)}")
        print(f"\n📊 Agent Trace ({len(triage_result.get('events', []))} events):")
        for event in triage_result.get("events", []):
            print(f"   [{event.get('node')}] {event.get('summary')}")
    else:
        print(f"   ⚠️ Result not ready yet. Check manually:")
        print(f"   curl http://localhost:8000/alerts/triage/{triage_id}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
