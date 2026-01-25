"""
Pydantic models for alert payloads and API responses.
"""
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MetricSnapshot(BaseModel):
    """Metric values at the time of alert."""
    
    latency_p95_ms: float | None = None
    latency_baseline_ms: float | None = None
    error_rate: float | None = None
    error_rate_baseline: float | None = None
    cpu_percent: float | None = None
    cpu_baseline: float | None = None
    memory_percent: float | None = None
    memory_baseline: float | None = None


class AlertContext(BaseModel):
    """Additional context for the alert."""
    
    recent_log_ids: list[str] = Field(default_factory=list)
    region: str | None = None
    deployment_version: str | None = None
    related_alerts: list[str] = Field(default_factory=list)


class AlertPayload(BaseModel):
    """
    Alert payload received from monitoring systems.
    
    This matches the JSON schema defined in the architecture:
    - service: Source microservice (auth-service, payment-service, etc.)
    - severity: Alert priority level
    - alert_type: Type of anomaly detected
    - detector: Detection method used
    - metric_snapshot: Metric values at alert time
    - context: Additional contextual information
    """
    
    id: UUID = Field(default_factory=uuid4)
    service: str
    severity: Literal["critical", "high", "medium", "low"]
    alert_type: Literal["latency_spike", "error_rate_spike", "cpu_anomaly", "memory_anomaly"]
    detector: Literal["threshold", "zscore", "spectral", "rolling_mean"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metric_snapshot: MetricSnapshot
    context: AlertContext = Field(default_factory=AlertContext)
    
    class Config:
        json_schema_extra = {
            "example": {
                "service": "auth-service",
                "severity": "critical",
                "alert_type": "latency_spike",
                "detector": "threshold",
                "timestamp": "2026-01-24T19:20:10Z",
                "metric_snapshot": {
                    "latency_p95_ms": 800,
                    "latency_baseline_ms": 120,
                    "error_rate": 0.14,
                    "error_rate_baseline": 0.01
                },
                "context": {
                    "recent_log_ids": ["log-001", "log-002"],
                    "region": "us-central1"
                }
            }
        }


class TriageResponse(BaseModel):
    """Response returned when an alert is queued for triage."""
    
    triage_id: UUID
    status: Literal["queued", "processing", "completed", "failed"] = "queued"
    message: str = "Alert queued for triage"


class TriageResult(BaseModel):
    """Result of the triage process."""
    
    triage_id: UUID
    alert_id: UUID
    service: str
    severity: str
    
    # Agent outputs
    logs_summary: str | None = None
    metrics_summary: str | None = None
    anomalies: list[str] = Field(default_factory=list)
    similar_incidents: list[dict] = Field(default_factory=list)
    
    # Decision
    hypothesis: str | None = None
    recommended_action: str | None = None
    confidence: float = 0.0
    requires_approval: bool = True
    
    # Trace for UI
    events: list[dict] = Field(default_factory=list)
    
    # Metadata
    status: Literal["pending", "approved", "rejected", "executed"] = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
