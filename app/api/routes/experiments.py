"""
Experiment API routes for A/B testing management.

Provides endpoints for:
- Viewing experiment configurations
- Getting experiment metrics and comparisons
- Running experiments on-demand
- Updating SRE feedback for accuracy tracking
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from app.agents.experiments.framework import (
    experiment_registry,
    ExperimentVariant,
    ExperimentConfig,
    ExperimentMetrics,
)


router = APIRouter(prefix="/experiments", tags=["experiments"])


class ExperimentSummary(BaseModel):
    """Summary of an experiment."""
    experiment_id: str
    variants: List[str]
    total_runs: int
    

class VariantStats(BaseModel):
    """Statistics for a variant."""
    variant: str
    total_runs: int
    accuracy: float
    avg_latency_ms: float
    avg_cost_usd: float
    avg_tokens: float
    false_positive_rate: float


class ExperimentComparison(BaseModel):
    """Comparison between experiment variants."""
    experiment_id: str
    variant_stats: Dict[str, VariantStats]
    recommendations: Dict[str, str]


class FeedbackUpdate(BaseModel):
    """SRE feedback for a triage run."""
    run_id: str
    was_approved: bool
    was_correct: Optional[bool] = None
    is_false_positive: Optional[bool] = None
    mttr_minutes: Optional[float] = None
    notes: Optional[str] = None


@router.get("/", response_model=List[ExperimentSummary])
async def list_experiments():
    """
    List all registered experiments.
    
    Returns summary information about each experiment.
    """
    experiments = []
    for exp_id, variants in experiment_registry._experiments.items():
        metrics = experiment_registry.get_metrics_by_experiment(exp_id)
        experiments.append(ExperimentSummary(
            experiment_id=exp_id,
            variants=[v.variant.value for v in variants],
            total_runs=len(metrics),
        ))
    return experiments


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    """
    Get details of a specific experiment.
    
    Returns variant configurations and current metrics.
    """
    if experiment_id not in experiment_registry._experiments:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    
    variants = experiment_registry._experiments[experiment_id]
    metrics = experiment_registry.get_metrics_by_experiment(experiment_id)
    
    return {
        "experiment_id": experiment_id,
        "variants": [
            {
                "variant": v.variant.value,
                "description": v.description,
                "model_provider": v.model_provider,
                "model_name": v.model_name,
                "use_rag": v.use_rag,
                "confidence_threshold": v.confidence_threshold,
                "is_shadow_mode": v.is_shadow_mode,
                "traffic_weight": v.traffic_weight,
            }
            for v in variants
        ],
        "total_runs": len(metrics),
        "metrics_summary": {
            "by_variant": {
                variant: len([m for m in metrics if m.variant == variant])
                for variant in set(m.variant for m in metrics)
            }
        }
    }


@router.get("/{experiment_id}/compare")
async def compare_variants(experiment_id: str):
    """
    Compare variant performance for an experiment.
    
    Returns aggregated statistics and recommendations for data-driven decisions.
    """
    if experiment_id not in experiment_registry._experiments:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    
    stats = experiment_registry.compute_variant_stats(experiment_id)
    
    if not stats:
        return {
            "experiment_id": experiment_id,
            "message": "No data available yet. Run some alerts through the system first.",
            "variant_stats": {},
            "recommendations": {},
        }
    
    # Generate recommendations
    recommendations = {}
    
    if stats:
        best_accuracy = max(stats.items(), key=lambda x: x[1].get("accuracy", 0))
        best_latency = min(stats.items(), key=lambda x: x[1].get("avg_latency_ms", float("inf")))
        best_cost = min(stats.items(), key=lambda x: x[1].get("avg_cost_usd", float("inf")))
        
        recommendations = {
            "best_accuracy": f"{best_accuracy[0]} ({best_accuracy[1].get('accuracy', 0):.1%})",
            "best_latency": f"{best_latency[0]} ({best_latency[1].get('avg_latency_ms', 0):.0f}ms)",
            "best_cost": f"{best_cost[0]} (${best_cost[1].get('avg_cost_usd', 0):.4f})",
        }
    
    return {
        "experiment_id": experiment_id,
        "variant_stats": stats,
        "recommendations": recommendations,
        "analysis_timestamp": datetime.now().isoformat(),
    }


@router.get("/{experiment_id}/metrics")
async def get_experiment_metrics(
    experiment_id: str,
    variant: Optional[str] = None,
    service: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
):
    """
    Get detailed metrics for an experiment.
    
    Supports filtering by variant, service, and severity for data slicing.
    """
    metrics = experiment_registry.get_metrics_by_experiment(experiment_id)
    
    # Apply filters
    if variant:
        metrics = [m for m in metrics if m.variant == variant]
    if service:
        metrics = [m for m in metrics if m.service == service]
    if severity:
        metrics = [m for m in metrics if m.severity == severity]
    
    # Sort by timestamp and limit
    metrics = sorted(metrics, key=lambda m: m.started_at, reverse=True)[:limit]
    
    return {
        "experiment_id": experiment_id,
        "filters": {"variant": variant, "service": service, "severity": severity},
        "total_matching": len(metrics),
        "metrics": [
            {
                "run_id": m.run_id,
                "variant": m.variant,
                "alert_id": m.alert_id,
                "alert_type": m.alert_type,
                "service": m.service,
                "severity": m.severity,
                "latency_ms": m.latency_ms,
                "token_usage": m.token_usage,
                "cost_usd": m.cost_usd,
                "was_approved": m.was_approved,
                "is_false_positive": m.is_false_positive,
                "started_at": m.started_at.isoformat(),
            }
            for m in metrics
        ],
    }


@router.post("/{experiment_id}/feedback")
async def submit_feedback(experiment_id: str, feedback: FeedbackUpdate):
    """
    Submit SRE feedback for a triage run.
    
    This updates accuracy and false positive tracking for the experiment.
    """
    # Find the metric and update it
    for metric in experiment_registry._metrics:
        if metric.run_id == feedback.run_id:
            metric.was_approved = feedback.was_approved
            if feedback.was_correct is not None:
                metric.was_correct = feedback.was_correct
            if feedback.is_false_positive is not None:
                metric.is_false_positive = feedback.is_false_positive
            if feedback.mttr_minutes is not None:
                metric.mttr_minutes = feedback.mttr_minutes
            
            return {
                "status": "updated",
                "run_id": feedback.run_id,
                "experiment_id": experiment_id,
            }
    
    raise HTTPException(status_code=404, detail=f"Run '{feedback.run_id}' not found")


@router.get("/langfuse/tags")
async def get_langfuse_tags():
    """
    Get available Langfuse tags for filtering traces.
    
    Use these tags in Langfuse dashboard to slice data by experiment.
    """
    variants = [v.value for v in ExperimentVariant]
    experiments = list(experiment_registry._experiments.keys())
    
    return {
        "available_tags": {
            "variant": [f"variant:{v}" for v in variants],
            "experiment": [f"experiment:{e}" for e in experiments],
            "mode": ["shadow", "production"],
        },
        "filter_examples": {
            "by_variant": "variant:control",
            "by_experiment": "experiment:model_comparison_v1",
            "shadow_runs": "shadow",
            "production_runs": "production",
        },
        "langfuse_url": "https://us.cloud.langfuse.com",
    }
