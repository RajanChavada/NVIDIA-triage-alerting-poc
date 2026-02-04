"""
Prometheus MCP Server - Model Context Protocol server for Prometheus integration.

Exposes tools that the agent can call autonomously:
- query_prometheus(): Execute PromQL queries
- list_metrics(): List available metrics
- get_alert_rules(): Get configured alert rules
- get_recording_rules(): Get recording rules

This is cleaner than hardcoding Prometheus queries in the agent's code.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import random

from langchain_core.tools import tool


# Mock Prometheus data for MVP
MOCK_METRICS = {
    "up": [
        {"instance": "auth-service:8080", "job": "kubernetes-pods", "value": 1},
        {"instance": "payment-service:8080", "job": "kubernetes-pods", "value": 1},
        {"instance": "gpu-node-1:9100", "job": "node-exporter", "value": 1},
    ],
    "http_requests_total": [
        {"service": "auth-service", "status": "200", "value": 125000},
        {"service": "auth-service", "status": "500", "value": 45},
        {"service": "payment-service", "status": "200", "value": 89000},
    ],
    "http_request_duration_seconds": [
        {"service": "auth-service", "quantile": "0.95", "value": 0.45},
        {"service": "auth-service", "quantile": "0.99", "value": 0.89},
        {"service": "payment-service", "quantile": "0.95", "value": 0.12},
    ],
    "container_memory_usage_bytes": [
        {"pod": "auth-service-abc123", "namespace": "production", "value": 512_000_000},
        {"pod": "payment-service-def456", "namespace": "production", "value": 256_000_000},
    ],
}


@tool
def query_prometheus(
    query: str,
    time_range: str = "5m",
    step: str = "15s"
) -> Dict[str, Any]:
    """
    Execute a PromQL query against Prometheus.
    
    Use this to fetch current metrics or historical data for analysis.
    Common queries:
    - rate(http_requests_total[5m]) - Request rate
    - histogram_quantile(0.95, http_request_duration_seconds) - P95 latency
    - sum(container_memory_usage_bytes) by (pod) - Memory by pod
    - DCGM_FI_DEV_GPU_TEMP{gpu="0"} - GPU temperature
    
    Args:
        query: PromQL query string
        time_range: Duration for range queries (e.g., "5m", "1h")
        step: Query resolution step
        
    Returns:
        Prometheus query result with data and metadata
    """
    # Parse the query to determine what mock data to return
    query_lower = query.lower()
    
    # Simulate query execution
    if "up" in query_lower:
        data = MOCK_METRICS["up"]
    elif "http_requests_total" in query_lower or "rate" in query_lower:
        data = MOCK_METRICS["http_requests_total"]
    elif "duration" in query_lower or "latency" in query_lower:
        data = MOCK_METRICS["http_request_duration_seconds"]
    elif "memory" in query_lower:
        data = MOCK_METRICS["container_memory_usage_bytes"]
    elif "dcgm" in query_lower:
        # Return GPU metrics
        from app.agents.tools.dcgm import get_dcgm_metrics
        gpu_metrics = get_dcgm_metrics.invoke({"gpu_id": 0})
        data = [{"metric": k, "value": v} for k, v in gpu_metrics.items() if isinstance(v, (int, float))]
    else:
        data = []
    
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": data,
        },
        "query": query,
        "executed_at": datetime.now().isoformat(),
    }


@tool
def query_prometheus_range(
    query: str,
    start: str = "-1h",
    end: str = "now",
    step: str = "1m"
) -> Dict[str, Any]:
    """
    Execute a range query for time-series data.
    
    Use this for trend analysis and anomaly detection.
    
    Args:
        query: PromQL query string
        start: Start time (relative like "-1h" or absolute ISO timestamp)
        end: End time (relative or absolute)
        step: Resolution step
        
    Returns:
        Time-series data with timestamps and values
    """
    # Generate mock time series
    now = datetime.now()
    points = []
    
    for i in range(60):  # Last hour, 1-min intervals
        timestamp = now - timedelta(minutes=i)
        value = 50 + random.uniform(-10, 10) + i * 0.1  # Slight upward trend
        points.append([timestamp.timestamp(), str(round(value, 2))])
    
    return {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"__name__": query.split("{")[0] if "{" in query else query},
                    "values": list(reversed(points)),
                }
            ],
        },
        "query": query,
    }


@tool
def list_metrics(
    filter_pattern: str = "",
    job_filter: str = ""
) -> List[str]:
    """
    List available Prometheus metrics matching a pattern.
    
    Use this to discover what metrics are available before querying.
    
    Args:
        filter_pattern: Regex pattern to filter metric names
        job_filter: Filter by job label
        
    Returns:
        List of matching metric names
    """
    all_metrics = [
        # Kubernetes metrics
        "up",
        "kube_pod_status_phase",
        "kube_deployment_status_replicas_available",
        "container_cpu_usage_seconds_total",
        "container_memory_usage_bytes",
        "container_network_receive_bytes_total",
        
        # HTTP metrics
        "http_requests_total",
        "http_request_duration_seconds",
        "http_request_size_bytes",
        "http_response_size_bytes",
        
        # Node metrics
        "node_cpu_seconds_total",
        "node_memory_MemAvailable_bytes",
        "node_disk_io_time_seconds_total",
        "node_network_receive_bytes_total",
        
        # DCGM GPU metrics
        "DCGM_FI_DEV_GPU_UTIL",
        "DCGM_FI_DEV_FB_FREE",
        "DCGM_FI_DEV_FB_USED",
        "DCGM_FI_DEV_POWER_USAGE",
        "DCGM_FI_DEV_GPU_TEMP",
        "DCGM_FI_DEV_SM_CLOCK",
        "DCGM_FI_DEV_MEM_CLOCK",
        "DCGM_FI_DEV_ENCODER_UTIL",
        "DCGM_FI_DEV_DECODER_UTIL",
        "DCGM_FI_DEV_PCIE_TX_THROUGHPUT",
        "DCGM_FI_DEV_PCIE_RX_THROUGHPUT",
        "DCGM_FI_DEV_XID_ERRORS",
    ]
    
    if filter_pattern:
        import re
        pattern = re.compile(filter_pattern, re.IGNORECASE)
        all_metrics = [m for m in all_metrics if pattern.search(m)]
    
    return all_metrics


@tool
def get_alert_rules() -> List[Dict]:
    """
    Get configured Prometheus alert rules.
    
    Use this to understand what conditions trigger alerts.
    
    Returns:
        List of alert rule definitions
    """
    return [
        {
            "name": "HighLatency",
            "expr": "histogram_quantile(0.95, http_request_duration_seconds) > 0.5",
            "for": "5m",
            "severity": "warning",
            "service": "all",
        },
        {
            "name": "HighErrorRate",
            "expr": "rate(http_requests_total{status=~'5..'}[5m]) / rate(http_requests_total[5m]) > 0.05",
            "for": "2m",
            "severity": "critical",
            "service": "all",
        },
        {
            "name": "GPUTemperatureHigh",
            "expr": "DCGM_FI_DEV_GPU_TEMP > 85",
            "for": "5m",
            "severity": "warning",
            "service": "gpu-cluster",
        },
        {
            "name": "GPUMemoryLow",
            "expr": "DCGM_FI_DEV_FB_FREE < 1000",
            "for": "5m",
            "severity": "critical",
            "service": "gpu-cluster",
        },
        {
            "name": "PodCrashLooping",
            "expr": "rate(kube_pod_container_status_restarts_total[15m]) > 0.1",
            "for": "10m",
            "severity": "critical",
            "service": "all",
        },
    ]


@tool  
def get_targets() -> List[Dict]:
    """
    Get Prometheus scrape targets and their health status.
    
    Use this to check if metrics collection is working.
    
    Returns:
        List of scrape targets with health status
    """
    return [
        {
            "labels": {"job": "kubernetes-pods", "instance": "auth-service:8080"},
            "health": "up",
            "lastScrape": datetime.now().isoformat(),
            "scrapeInterval": "15s",
        },
        {
            "labels": {"job": "kubernetes-pods", "instance": "payment-service:8080"},
            "health": "up",
            "lastScrape": datetime.now().isoformat(),
            "scrapeInterval": "15s",
        },
        {
            "labels": {"job": "dcgm-exporter", "instance": "gpu-node-1:9400"},
            "health": "up",
            "lastScrape": datetime.now().isoformat(),
            "scrapeInterval": "10s",
        },
        {
            "labels": {"job": "dcgm-exporter", "instance": "gpu-node-2:9400"},
            "health": "down",
            "lastError": "connection refused",
            "lastScrape": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "scrapeInterval": "10s",
        },
    ]


class PrometheusMCPServer:
    """
    MCP Server wrapper for Prometheus tools.
    
    This class packages the tools for MCP protocol compatibility.
    In production, this would implement the full MCP specification.
    """
    
    def __init__(self, prometheus_url: str = "http://prometheus:9090"):
        self.prometheus_url = prometheus_url
        self.tools = [
            query_prometheus,
            query_prometheus_range,
            list_metrics,
            get_alert_rules,
            get_targets,
        ]
    
    def list_tools(self) -> List[str]:
        """List available tools."""
        return [t.name for t in self.tools]
    
    def get_tool(self, name: str):
        """Get a tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
