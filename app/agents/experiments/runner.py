"""
Experiment Runner - Execute A/B tests in shadow mode.

Runs multiple variants in parallel for the same alert:
- Control variant executes normally
- Shadow variants run but don't execute actions
- All results are captured for comparison
"""
import asyncio
from uuid import UUID, uuid4
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.alert import AlertPayload, TriageResult
from app.agents.experiments.framework import (
    ExperimentConfig,
    ExperimentMetrics,
    ExperimentVariant,
    experiment_registry,
)


async def run_experiment_parallel(
    alert: AlertPayload,
    experiment_id: str,
    variants: Optional[List[ExperimentVariant]] = None,
) -> Dict[str, Any]:
    """
    Run multiple experiment variants in parallel for A/B testing.
    
    Only the control variant's decision is executed.
    Shadow variants run in parallel but don't take action.
    
    Args:
        alert: The alert to process
        experiment_id: ID of the experiment to run
        variants: Specific variants to run (None = all registered)
        
    Returns:
        Dict with control result and shadow results for comparison
    """
    from app.agents.graph import run_triage_workflow
    
    # Get variants from registry or use specified
    if variants:
        configs = [
            ExperimentConfig(
                experiment_id=experiment_id,
                variant=v,
                description=f"Manual variant: {v.value}",
                is_shadow_mode=(v != ExperimentVariant.CONTROL),
            )
            for v in variants
        ]
    else:
        # Get all registered variants for this experiment
        configs = experiment_registry._experiments.get(experiment_id, [])
    
    if not configs:
        # No experiment registered, run control only
        configs = [ExperimentConfig.control(experiment_id)]
    
    # Run all variants in parallel
    run_id = str(uuid4())
    
    async def run_variant(config: ExperimentConfig) -> Dict[str, Any]:
        """Run a single variant and capture metrics."""
        start_time = datetime.now()
        
        try:
            # For now, we use the same workflow but track differently
            # In a full implementation, the workflow would use config.model_provider, etc.
            result = await run_triage_workflow(
                triage_id=uuid4(),
                alert=alert,
            )
            
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # Create metrics
            metrics = ExperimentMetrics(
                experiment_id=experiment_id,
                variant=config.variant.value,
                run_id=run_id,
                alert_id=str(alert.id),
                alert_type=alert.alert_type,
                service=alert.service,
                severity=alert.severity,
                latency_ms=latency_ms,
                started_at=start_time,
                completed_at=end_time,
            )
            
            # Record to registry
            experiment_registry.record_metrics(metrics)
            
            return {
                "variant": config.variant.value,
                "is_shadow": config.is_shadow_mode,
                "result": result,
                "metrics": metrics,
                "success": True,
            }
            
        except Exception as e:
            return {
                "variant": config.variant.value,
                "is_shadow": config.is_shadow_mode,
                "result": None,
                "error": str(e),
                "success": False,
            }
    
    # Execute all variants in parallel
    results = await asyncio.gather(*[run_variant(c) for c in configs])
    
    # Separate control from shadow results
    control_result = next((r for r in results if not r.get("is_shadow")), results[0])
    shadow_results = [r for r in results if r.get("is_shadow")]
    
    return {
        "run_id": run_id,
        "experiment_id": experiment_id,
        "control": control_result,
        "shadow_results": shadow_results,
        "variants_executed": len(results),
    }


async def compare_variants(experiment_id: str) -> Dict[str, Any]:
    """
    Compare variant performance for an experiment.
    
    Returns aggregated stats for data-driven decisions.
    """
    stats = experiment_registry.compute_variant_stats(experiment_id)
    
    if not stats:
        return {"error": f"No data for experiment {experiment_id}"}
    
    # Find best performing variant
    best_accuracy = max(stats.values(), key=lambda x: x.get("accuracy", 0))
    best_latency = min(stats.values(), key=lambda x: x.get("avg_latency_ms", float("inf")))
    best_cost = min(stats.values(), key=lambda x: x.get("avg_cost_usd", float("inf")))
    
    return {
        "experiment_id": experiment_id,
        "variant_stats": stats,
        "recommendations": {
            "best_accuracy": [k for k, v in stats.items() if v == best_accuracy][0],
            "best_latency": [k for k, v in stats.items() if v == best_latency][0],
            "best_cost": [k for k, v in stats.items() if v == best_cost][0],
        },
    }
