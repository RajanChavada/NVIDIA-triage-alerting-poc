"""
Experiment Framework for A/B Testing Agent Variants.

Supports:
- Prompt variants (full RAG vs simplified)
- Model variants (Nemotron vs Claude vs Gemini)
- Confidence threshold variations
- Shadow mode for non-destructive testing
- Langfuse integration for tracking
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any
from datetime import datetime
import random
import uuid


class ExperimentVariant(Enum):
    """Available experiment variants."""
    CONTROL = "control"           # Current: Full RAG + Claude/OpenRouter
    SIMPLIFIED_PROMPT = "simplified_prompt"  # No RAG, simpler prompts
    NEMOTRON = "nemotron"         # NVIDIA Nemotron model
    LOW_THRESHOLD = "low_threshold"  # Lower confidence threshold (50%)
    HIGH_THRESHOLD = "high_threshold"  # Higher confidence threshold (90%)
    PARALLEL_TOOLS = "parallel_tools"  # Parallel tool execution


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment variant."""
    experiment_id: str
    variant: ExperimentVariant
    description: str
    
    # Model configuration
    model_provider: str = "openrouter"  # gemini, openrouter, nvidia
    model_name: str = "anthropic/claude-3.5-sonnet"
    
    # Prompt configuration
    use_rag: bool = True
    prompt_template: str = "default"
    
    # Threshold configuration
    confidence_threshold: float = 0.7
    auto_approve_threshold: float = 0.85
    
    # Execution mode
    is_shadow_mode: bool = False  # If True, don't execute actions
    
    # Weights for random selection
    traffic_weight: float = 1.0
    
    @classmethod
    def control(cls, experiment_id: str) -> "ExperimentConfig":
        """Create control variant (current production behavior)."""
        return cls(
            experiment_id=experiment_id,
            variant=ExperimentVariant.CONTROL,
            description="Control: Full RAG with Claude 3.5 Sonnet",
            model_provider="openrouter",
            model_name="anthropic/claude-3.5-sonnet",
            use_rag=True,
            is_shadow_mode=False,
        )
    
    @classmethod
    def nemotron_variant(cls, experiment_id: str) -> "ExperimentConfig":
        """Create NVIDIA Nemotron variant."""
        return cls(
            experiment_id=experiment_id,
            variant=ExperimentVariant.NEMOTRON,
            description="NVIDIA Nemotron 70B for triage",
            model_provider="nvidia",
            model_name="nvidia/llama-3.1-nemotron-70b-instruct",
            use_rag=True,
            is_shadow_mode=True,  # Shadow mode until validated
        )
    
    @classmethod
    def simplified_variant(cls, experiment_id: str) -> "ExperimentConfig":
        """Create simplified prompt variant (no RAG)."""
        return cls(
            experiment_id=experiment_id,
            variant=ExperimentVariant.SIMPLIFIED_PROMPT,
            description="Simplified: No RAG, faster processing",
            model_provider="openrouter",
            model_name="anthropic/claude-3.5-sonnet",
            use_rag=False,
            prompt_template="simplified",
            is_shadow_mode=True,
        )


@dataclass
class ExperimentMetrics:
    """Metrics captured for each experiment run."""
    experiment_id: str
    variant: str
    run_id: str
    
    # Alert context
    alert_id: str
    alert_type: str
    service: str
    severity: str
    
    # Performance metrics
    latency_ms: float = 0.0
    token_usage: int = 0
    cost_usd: float = 0.0
    
    # Quality metrics (updated after SRE feedback)
    was_approved: Optional[bool] = None  # SRE approved the recommendation?
    was_correct: Optional[bool] = None   # Retrospective: was decision correct?
    is_false_positive: Optional[bool] = None
    
    # Timing metrics
    mttr_minutes: Optional[float] = None  # Mean time to resolution
    escalation_rate: Optional[float] = None
    
    # Timestamps
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_langfuse_metadata(self) -> Dict[str, Any]:
        """Convert to Langfuse-compatible metadata dict."""
        return {
            "experiment_id": self.experiment_id,
            "variant": self.variant,
            "run_id": self.run_id,
            "alert_type": self.alert_type,
            "service": self.service,
            "severity": self.severity,
            "latency_ms": self.latency_ms,
            "token_usage": self.token_usage,
            "cost_usd": self.cost_usd,
        }
    
    def to_langfuse_tags(self) -> List[str]:
        """Generate tags for Langfuse filtering."""
        return [
            f"experiment:{self.experiment_id}",
            f"variant:{self.variant}",
            f"alert_type:{self.alert_type}",
            f"service:{self.service}",
            f"severity:{self.severity}",
        ]


class ExperimentRegistry:
    """
    Registry of active experiments.
    
    Manages experiment configurations and traffic allocation.
    """
    
    def __init__(self):
        self._experiments: Dict[str, List[ExperimentConfig]] = {}
        self._metrics: List[ExperimentMetrics] = []
    
    def register_experiment(self, experiment_id: str, variants: List[ExperimentConfig]):
        """Register a new experiment with its variants."""
        self._experiments[experiment_id] = variants
        print(f"📊 Registered experiment '{experiment_id}' with {len(variants)} variants")
    
    def get_variant(self, experiment_id: str) -> Optional[ExperimentConfig]:
        """
        Get a variant for an experiment based on traffic weights.
        
        Uses weighted random selection.
        """
        if experiment_id not in self._experiments:
            return None
        
        variants = self._experiments[experiment_id]
        weights = [v.traffic_weight for v in variants]
        total = sum(weights)
        normalized = [w / total for w in weights]
        
        return random.choices(variants, weights=normalized, k=1)[0]
    
    def record_metrics(self, metrics: ExperimentMetrics):
        """Record metrics for an experiment run."""
        self._metrics.append(metrics)
    
    def get_metrics_by_experiment(self, experiment_id: str) -> List[ExperimentMetrics]:
        """Get all metrics for an experiment."""
        return [m for m in self._metrics if m.experiment_id == experiment_id]
    
    def get_metrics_by_variant(self, variant: str) -> List[ExperimentMetrics]:
        """Get all metrics for a specific variant."""
        return [m for m in self._metrics if m.variant == variant]
    
    def compute_variant_stats(self, experiment_id: str) -> Dict[str, Dict[str, float]]:
        """
        Compute aggregate statistics per variant.
        
        Returns metrics for comparison:
        - accuracy: % approved by SRE
        - avg_latency_ms
        - avg_cost_usd
        - avg_token_usage
        - escalation_rate
        """
        stats = {}
        
        for variant in ExperimentVariant:
            variant_metrics = [
                m for m in self._metrics 
                if m.experiment_id == experiment_id and m.variant == variant.value
            ]
            
            if not variant_metrics:
                continue
            
            approved = [m for m in variant_metrics if m.was_approved is not None]
            
            stats[variant.value] = {
                "total_runs": len(variant_metrics),
                "accuracy": sum(1 for m in approved if m.was_approved) / len(approved) if approved else 0,
                "avg_latency_ms": sum(m.latency_ms for m in variant_metrics) / len(variant_metrics),
                "avg_cost_usd": sum(m.cost_usd for m in variant_metrics) / len(variant_metrics),
                "avg_tokens": sum(m.token_usage for m in variant_metrics) / len(variant_metrics),
                "false_positive_rate": sum(1 for m in variant_metrics if m.is_false_positive) / len(variant_metrics),
            }
        
        return stats


# Global experiment registry
experiment_registry = ExperimentRegistry()


def setup_default_experiments():
    """Set up default A/B experiments."""
    
    # Experiment 1: Model comparison
    experiment_registry.register_experiment(
        "model_comparison_v1",
        [
            ExperimentConfig.control("model_comparison_v1"),
            ExperimentConfig.nemotron_variant("model_comparison_v1"),
        ]
    )
    
    # Experiment 2: RAG vs No-RAG
    experiment_registry.register_experiment(
        "rag_ablation_v1",
        [
            ExperimentConfig.control("rag_ablation_v1"),
            ExperimentConfig.simplified_variant("rag_ablation_v1"),
        ]
    )


# Initialize default experiments
setup_default_experiments()
