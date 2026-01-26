"""
Prometheus Tool - Mock metrics fetching logic for NVIDIA clusters.
"""
from typing import Dict, Any
import random
from datetime import datetime, timedelta

def fetch_prometheus_metrics(service_name: str, metric_name: str, time_range_minutes: int = 15) -> Dict[str, Any]:
    """
    Mock fetching metrics from Prometheus for a specific service.
    
    In a real scenario, this would call NVIDIA's Prometheus API.
    """
    print(f"🔍 [TOOL] Querying Prometheus for {service_name}/{metric_name}...")
    
    # Simulate API latency
    import time
    time.sleep(1.5)
    
    # Mock data generation based on service and metric
    now = datetime.utcnow()
    timestamps = [(now - timedelta(minutes=m)).isoformat() for m in range(time_range_minutes)]
    
    # Generate some slightly anomalous data if it's a spike/anomaly
    base_val = 100 if "cpu" in metric_name else 0.05
    values = [base_val * (1 + random.uniform(-0.1, 0.1)) for _ in range(time_range_minutes)]
    
    # Simulate a spike in the last 2 minutes
    values[0] *= 3.5
    values[1] *= 2.8
    
    return {
        "service": service_name,
        "metric": metric_name,
        "time_range": f"{time_range_minutes}m",
        "data_points": [
            {"ts": ts, "val": round(v, 4)} for ts, v in zip(timestamps, values)
        ],
        "summary": {
            "mean": round(sum(values) / len(values), 4),
            "max": round(max(values), 4),
            "p95": round(sorted(values)[int(len(values) * 0.95)], 4)
        }
    }

# LangChain Tool Definition
from langchain_core.tools import tool

@tool
def get_service_metrics(service_name: str, metric_name: str):
    """
    Fetch historical metrics (CPU, Memory, Latency, Error Rate) for a specific NVIDIA service.
    Use this to identify spikes or trends that correlate with an alert.
    """
    return fetch_prometheus_metrics(service_name, metric_name)
