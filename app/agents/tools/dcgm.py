"""
DCGM (Data Center GPU Manager) metrics tool.

Provides access to NVIDIA GPU metrics via DCGM Exporter:
- DCGM_FI_DEV_GPU_UTIL: GPU utilization %
- DCGM_FI_DEV_FB_FREE: Framebuffer memory free (MB)
- DCGM_FI_DEV_POWER_USAGE: Power consumption (W)
- DCGM_FI_DEV_GPU_TEMP: Temperature (°C)
- DCGM_FI_DEV_ENCODER_UTIL: Encoder utilization %
- DCGM_FI_DEV_DECODER_UTIL: Decoder utilization %

In production, these metrics come from DCGM Exporter → Prometheus.
For MVP, we provide mock data with realistic patterns.
"""
from typing import Dict, List, Optional
from langchain_core.tools import tool
import random
from datetime import datetime, timedelta

from app.config import settings


# Mock historical data for demo purposes
MOCK_GPU_METRICS = {
    "healthy": {
        "DCGM_FI_DEV_GPU_UTIL": (45, 65),  # (min, max) range
        "DCGM_FI_DEV_FB_FREE": (8000, 12000),  # MB
        "DCGM_FI_DEV_POWER_USAGE": (150, 200),  # W
        "DCGM_FI_DEV_GPU_TEMP": (55, 70),  # °C
        "DCGM_FI_DEV_ENCODER_UTIL": (10, 30),  # %
        "DCGM_FI_DEV_DECODER_UTIL": (5, 15),  # %
    },
    "stressed": {
        "DCGM_FI_DEV_GPU_UTIL": (85, 100),
        "DCGM_FI_DEV_FB_FREE": (500, 2000),
        "DCGM_FI_DEV_POWER_USAGE": (280, 350),
        "DCGM_FI_DEV_GPU_TEMP": (80, 95),
        "DCGM_FI_DEV_ENCODER_UTIL": (70, 95),
        "DCGM_FI_DEV_DECODER_UTIL": (60, 85),
    },
    "failing": {
        "DCGM_FI_DEV_GPU_UTIL": (0, 15),  # Low util indicates issues
        "DCGM_FI_DEV_FB_FREE": (100, 500),
        "DCGM_FI_DEV_POWER_USAGE": (50, 100),  # Power drops
        "DCGM_FI_DEV_GPU_TEMP": (90, 105),  # Overheating
        "DCGM_FI_DEV_ENCODER_UTIL": (0, 5),
        "DCGM_FI_DEV_DECODER_UTIL": (0, 5),
    },
}


def _generate_mock_value(metric_name: str, state: str = "healthy") -> float:
    """Generate realistic mock value for a metric."""
    ranges = MOCK_GPU_METRICS.get(state, MOCK_GPU_METRICS["healthy"])
    if metric_name in ranges:
        min_val, max_val = ranges[metric_name]
        return round(random.uniform(min_val, max_val), 2)
    return 0.0


@tool
def get_dcgm_metrics(
    gpu_id: int = 0,
    node_name: str = "gpu-node-1"
) -> Dict[str, float]:
    """
    Query DCGM metrics for a specific GPU.
    
    Use this tool to get current GPU health metrics including:
    - GPU utilization percentage
    - Free framebuffer memory (MB)
    - Power consumption (Watts)
    - GPU temperature (Celsius)
    - Encoder/decoder utilization
    
    Args:
        gpu_id: GPU device ID (0-indexed)
        node_name: Name of the K8s node hosting the GPU
        
    Returns:
        Dictionary of DCGM metrics with their current values
    """
    # In production, this would query DCGM Exporter or Prometheus
    # For MVP, return realistic mock data
    
    # Simulate occasional stressed/failing GPUs
    state = random.choices(
        ["healthy", "stressed", "failing"],
        weights=[0.7, 0.2, 0.1]
    )[0]
    
    metrics = {
        "gpu_id": gpu_id,
        "node_name": node_name,
        "state": state,
        "timestamp": datetime.now().isoformat(),
        "DCGM_FI_DEV_GPU_UTIL": _generate_mock_value("DCGM_FI_DEV_GPU_UTIL", state),
        "DCGM_FI_DEV_FB_FREE": _generate_mock_value("DCGM_FI_DEV_FB_FREE", state),
        "DCGM_FI_DEV_POWER_USAGE": _generate_mock_value("DCGM_FI_DEV_POWER_USAGE", state),
        "DCGM_FI_DEV_GPU_TEMP": _generate_mock_value("DCGM_FI_DEV_GPU_TEMP", state),
        "DCGM_FI_DEV_ENCODER_UTIL": _generate_mock_value("DCGM_FI_DEV_ENCODER_UTIL", state),
        "DCGM_FI_DEV_DECODER_UTIL": _generate_mock_value("DCGM_FI_DEV_DECODER_UTIL", state),
    }
    
    # Add health assessment
    metrics["health_status"] = _assess_gpu_health(metrics)
    
    return metrics


@tool
def get_dcgm_history(
    gpu_id: int = 0,
    metric_name: str = "DCGM_FI_DEV_GPU_TEMP",
    hours: int = 1
) -> List[Dict]:
    """
    Get historical DCGM metrics for trend analysis.
    
    Use this to identify patterns before failures:
    - Temperature spikes + power drops → potential thermal throttling
    - Memory drops + low utilization → potential OOM approaching
    
    Args:
        gpu_id: GPU device ID
        metric_name: Specific DCGM metric to query
        hours: Number of hours of history to retrieve
        
    Returns:
        List of timestamped metric values
    """
    # Generate mock historical data with realistic patterns
    history = []
    now = datetime.now()
    
    # Simulate gradual degradation pattern
    for i in range(hours * 12):  # 5-minute intervals
        timestamp = now - timedelta(minutes=i * 5)
        
        # Simulate trending pattern (gradual increase for temp)
        if metric_name == "DCGM_FI_DEV_GPU_TEMP":
            base_value = 60 + (hours * 12 - i) * 0.3  # Gradual increase
            value = base_value + random.uniform(-2, 2)
        else:
            value = _generate_mock_value(metric_name)
        
        history.append({
            "timestamp": timestamp.isoformat(),
            "value": round(value, 2),
            "gpu_id": gpu_id,
        })
    
    return list(reversed(history))  # Oldest first


@tool
def list_dcgm_gpus() -> List[Dict]:
    """
    List all GPUs monitored by DCGM in the cluster.
    
    Returns:
        List of GPU devices with their node assignments
    """
    # Mock GPU inventory
    return [
        {
            "gpu_id": 0,
            "node_name": "gpu-node-1",
            "gpu_model": "NVIDIA A100-SXM4-80GB",
            "driver_version": "535.104.12",
            "cuda_version": "12.2",
            "status": "healthy",
        },
        {
            "gpu_id": 1,
            "node_name": "gpu-node-1",
            "gpu_model": "NVIDIA A100-SXM4-80GB",
            "driver_version": "535.104.12",
            "cuda_version": "12.2",
            "status": "healthy",
        },
        {
            "gpu_id": 0,
            "node_name": "gpu-node-2",
            "gpu_model": "NVIDIA A100-SXM4-80GB",
            "driver_version": "535.104.12",
            "cuda_version": "12.2",
            "status": "stressed",
        },
    ]


def _assess_gpu_health(metrics: Dict) -> str:
    """Assess GPU health from metrics."""
    issues = []
    
    if metrics.get("DCGM_FI_DEV_GPU_TEMP", 0) > 85:
        issues.append("HIGH_TEMPERATURE")
    
    if metrics.get("DCGM_FI_DEV_FB_FREE", float("inf")) < 1000:
        issues.append("LOW_MEMORY")
    
    if metrics.get("DCGM_FI_DEV_POWER_USAGE", 0) > 300:
        issues.append("HIGH_POWER")
    
    if metrics.get("DCGM_FI_DEV_GPU_UTIL", 100) < 10 and metrics.get("DCGM_FI_DEV_GPU_TEMP", 0) > 80:
        issues.append("THERMAL_THROTTLING")
    
    if issues:
        return f"WARNING: {', '.join(issues)}"
    return "HEALTHY"


# Prometheus query helper for production use
def query_prometheus_dcgm(query: str, endpoint: str = None) -> Dict:
    """
    Query Prometheus for DCGM metrics (production implementation).
    
    This is a stub - in production, would use httpx to query Prometheus.
    """
    import httpx
    
    endpoint = endpoint or "http://prometheus:9090"
    
    try:
        response = httpx.get(
            f"{endpoint}/api/v1/query",
            params={"query": query},
            timeout=5.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "query": query}
