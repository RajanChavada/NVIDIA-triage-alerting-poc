"""
Observability Module - Track agent performance metrics.

Captures:
- Token usage per node
- Latency per node
- Cost per triage
- LLM model used

This can be synced to Langfuse or displayed directly in Streamlit.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json


@dataclass
class NodeMetrics:
    """Metrics for a single agent node execution."""
    node_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    llm_model: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tool_calls: int = 0
    cost_usd: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass
class TriageMetrics:
    """Aggregated metrics for entire triage session."""
    triage_id: str
    alert_id: str
    service: str
    start_time: datetime
    end_time: Optional[datetime] = None
    node_metrics: List[NodeMetrics] = field(default_factory=list)
    
    # Experiment tracking
    experiment_id: Optional[str] = None
    variant: Optional[str] = None
    alert_type: Optional[str] = None
    severity: Optional[str] = None
    
    # Quality metrics (updated after SRE feedback)
    was_approved: Optional[bool] = None  # SRE approved recommendation?
    is_false_positive: Optional[bool] = None  # Retrospective analysis
    mttr_minutes: Optional[float] = None  # Mean time to resolution
    
    @property
    def total_duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0
    
    @property
    def total_tokens(self) -> int:
        return sum(m.total_tokens for m in self.node_metrics)
    
    @property
    def total_cost_usd(self) -> float:
        return sum(m.cost_usd for m in self.node_metrics)
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "triage_id": self.triage_id,
            "alert_id": self.alert_id,
            "service": self.service,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_ms": self.total_duration_ms,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "node_metrics": [
                {
                    "node_name": m.node_name,
                    "duration_ms": m.duration_ms,
                    "llm_model": m.llm_model,
                    "total_tokens": m.total_tokens,
                    "tool_calls": m.tool_calls,
                    "cost_usd": m.cost_usd,
                }
                for m in self.node_metrics
            ],
        }


# In-memory store (replace with database in production)
_metrics_store: Dict[str, TriageMetrics] = {}


def start_triage_metrics(triage_id: str, alert_id: str, service: str) -> TriageMetrics:
    """Start tracking metrics for a new triage session."""
    metrics = TriageMetrics(
        triage_id=triage_id,
        alert_id=alert_id,
        service=service,
        start_time=datetime.now(),
    )
    _metrics_store[triage_id] = metrics
    return metrics


def add_node_metrics(triage_id: str, node_metrics: NodeMetrics):
    """Add node-level metrics to a triage session."""
    if triage_id in _metrics_store:
        _metrics_store[triage_id].node_metrics.append(node_metrics)


def end_triage_metrics(triage_id: str):
    """Mark triage as complete."""
    if triage_id in _metrics_store:
        _metrics_store[triage_id].end_time = datetime.now()


def get_triage_metrics(triage_id: str) -> TriageMetrics | None:
    """Get metrics for a specific triage."""
    return _metrics_store.get(triage_id)


def get_all_metrics() -> List[TriageMetrics]:
    """Get all metrics (for dashboard)."""
    return list(_metrics_store.values())


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate cost based on model and token counts.
    
    Pricing (as of Jan 2026):
    - gemini-2.5-flash: $0.075 / 1M input, $0.30 / 1M output
    - gpt-5.2: $5.00 / 1M input, $15.00 / 1M output
    """
    pricing = {
        "gemini-2.0-flash": {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
        "anthropic/claude-3.5-sonnet": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
        # NVIDIA Nemotron pricing (via API Catalog)
        "nvidia/llama-3.1-nemotron-70b-instruct": {"input": 0.35 / 1_000_000, "output": 0.40 / 1_000_000},
        "nvidia/mistral-nemo-12b-instruct": {"input": 0.10 / 1_000_000, "output": 0.10 / 1_000_000},
    }
    
    if model in pricing:
        input_cost = prompt_tokens * pricing[model]["input"]
        output_cost = completion_tokens * pricing[model]["output"]
        return input_cost + output_cost
    
    # Fallback estimate
    return (prompt_tokens + completion_tokens) * 0.0001 / 1000
