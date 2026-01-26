"""
Alert Generation Service - Generates synthetic alerts for demo and testing.
"""
import random
from datetime import datetime
from pathlib import Path
import yaml
from app.models.alert import AlertPayload

# Registry location
SERVICES_PATH = Path(__file__).parent.parent.parent / "synthetic" / "services.yaml"

def load_registry():
    """Load services registry."""
    with open(SERVICES_PATH) as f:
        return yaml.safe_load(f)

def generate_synthetic_alert(service_name: str | None = None, alert_type: str | None = None) -> AlertPayload:
    """
    Generate a realistic fake alert.
    If service_name is provided, generates alert only for that service.
    If alert_type is provided, generates that specific type of alert.
    """
    config = load_registry()
    services = config["services"]
    alert_types = config["alert_types"]
    detectors = config["detectors"]
    
    # Filter or pick random service
    if service_name:
        service = next((s for s in services if s["name"] == service_name), services[0])
    else:
        service = random.choice(services)
        
    s_name = service["name"]
    
    # Pick or use provided alert type & detector
    a_type = alert_type if alert_type and alert_type in alert_types else random.choice(alert_types)
    detector = random.choice(detectors)
    
    # Generate metric snapshot with anomaly
    metric_snapshot = {}
    for metric in service.get("metrics", []):
        baseline = metric["baseline"]
        metric_name = metric["name"]
        
        # Determine multiplier based on alert type
        multiplier = random.uniform(2.0, 10.0)
        if a_type == "latency_spike" and "latency" in metric_name:
            multiplier = random.uniform(5.0, 15.0)
        elif a_type == "error_rate_spike" and "error" in metric_name:
            multiplier = random.uniform(8.0, 20.0)
        elif a_type == "cpu_anomaly" and "cpu" in metric_name:
            multiplier = random.uniform(2.5, 3.0) # Assume CPU maxes at 100
            
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
    
    # Determine severity
    criticality = service.get("criticality", "medium")
    severity = "critical" if criticality == "critical" or a_type == "latency_spike" else (
        "high" if criticality == "high" else "medium"
    )
    
    return AlertPayload(
        service=s_name,
        severity=severity,
        alert_type=a_type,
        detector=detector,
        timestamp=datetime.utcnow().isoformat() + "Z",
        metric_snapshot=metric_snapshot,
        context={
            "recent_log_ids": [f"log-{random.randint(1000, 9999)}" for _ in range(3)],
            "region": service.get("region", "us-central1"),
        }
    )
