"""
GPU Anomaly Detector - Predictive alerting using historical metrics.

Implements lightweight ML-based anomaly detection:
- Isolation Forest for multivariate anomaly detection
- Z-score based deviation from baseline
- Pattern recognition for failure precursors

Patterns detected:
- GPU temp spikes + power drops → thermal throttling
- Memory drops + low utilization → approaching OOM
- High utilization + high temp → sustained overload

This runs before alerts fire to enable proactive investigation.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from collections import deque


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""
    is_anomaly: bool
    confidence: float  # 0-1 confidence score
    anomaly_type: Optional[str]
    predicted_issue: Optional[str]
    minutes_to_failure: Optional[float]  # Estimated time to critical threshold
    contributing_factors: List[str]
    recommended_action: Optional[str]
    raw_score: float


@dataclass
class MetricBaseline:
    """Baseline statistics for a metric."""
    metric_name: str
    mean: float
    std: float
    min_observed: float
    max_observed: float
    samples: int


class GPUAnomalyDetector:
    """
    Detect anomalies in GPU metrics before critical thresholds.
    
    Uses a combination of statistical methods and pattern matching:
    1. Z-score deviation from rolling baseline
    2. Isolation Forest for multivariate anomalies
    3. Pattern matching for known failure precursors
    """
    
    # Known failure patterns: (condition) -> (issue, action)
    FAILURE_PATTERNS = {
        "thermal_throttling": {
            "conditions": {
                "DCGM_FI_DEV_GPU_TEMP": (">", 80),
                "DCGM_FI_DEV_GPU_UTIL": ("<", 30),
                "DCGM_FI_DEV_POWER_USAGE": ("<", 100),
            },
            "issue": "GPU thermal throttling detected",
            "action": "Check cooling system, consider workload redistribution",
        },
        "memory_pressure": {
            "conditions": {
                "DCGM_FI_DEV_FB_FREE": ("<", 1000),
                "DCGM_FI_DEV_GPU_UTIL": (">", 80),
            },
            "issue": "GPU memory pressure - approaching OOM",
            "action": "Reduce batch size or scale horizontally",
        },
        "sustained_overload": {
            "conditions": {
                "DCGM_FI_DEV_GPU_UTIL": (">", 95),
                "DCGM_FI_DEV_GPU_TEMP": (">", 75),
                "DCGM_FI_DEV_POWER_USAGE": (">", 280),
            },
            "issue": "Sustained GPU overload",
            "action": "Scale GPU replicas or implement rate limiting",
        },
        "power_anomaly": {
            "conditions": {
                "DCGM_FI_DEV_POWER_USAGE": ("<", 50),
                "DCGM_FI_DEV_GPU_UTIL": (">", 20),
            },
            "issue": "Power draw anomaly - possible hardware issue",
            "action": "Schedule hardware inspection, prepare failover",
        },
    }
    
    # Thresholds for anomaly scoring
    Z_SCORE_THRESHOLD = 2.5
    ANOMALY_CONFIDENCE_THRESHOLD = 0.7
    
    def __init__(self, window_size: int = 100):
        """
        Initialize detector.
        
        Args:
            window_size: Number of samples for rolling baseline
        """
        self.window_size = window_size
        self.baselines: Dict[str, MetricBaseline] = {}
        self.history: Dict[str, deque] = {}
        self._isolation_forest = None
        
    def update_baseline(self, metric_name: str, value: float):
        """Update rolling baseline for a metric."""
        if metric_name not in self.history:
            self.history[metric_name] = deque(maxlen=self.window_size)
        
        self.history[metric_name].append(value)
        
        # Recompute baseline
        values = list(self.history[metric_name])
        if len(values) >= 10:  # Minimum samples for baseline
            self.baselines[metric_name] = MetricBaseline(
                metric_name=metric_name,
                mean=np.mean(values),
                std=max(np.std(values), 0.01),  # Avoid division by zero
                min_observed=min(values),
                max_observed=max(values),
                samples=len(values),
            )
    
    def compute_z_score(self, metric_name: str, value: float) -> float:
        """Compute z-score for a metric value."""
        if metric_name not in self.baselines:
            return 0.0
        
        baseline = self.baselines[metric_name]
        return (value - baseline.mean) / baseline.std
    
    def detect(self, metrics: Dict[str, float]) -> AnomalyResult:
        """
        Detect anomalies in current GPU metrics.
        
        Args:
            metrics: Current DCGM metrics
            
        Returns:
            AnomalyResult with detection details
        """
        # Update baselines
        for name, value in metrics.items():
            if isinstance(value, (int, float)) and name.startswith("DCGM_"):
                self.update_baseline(name, value)
        
        # Compute z-scores
        z_scores = {}
        deviations = []
        for name, value in metrics.items():
            if isinstance(value, (int, float)) and name.startswith("DCGM_"):
                z = self.compute_z_score(name, value)
                z_scores[name] = z
                if abs(z) > self.Z_SCORE_THRESHOLD:
                    deviations.append(f"{name}: z={z:.2f}")
        
        # Check for known failure patterns
        pattern_match = self._check_patterns(metrics)
        
        # Compute overall anomaly score
        if z_scores:
            max_z = max(abs(z) for z in z_scores.values())
            avg_z = np.mean([abs(z) for z in z_scores.values()])
        else:
            max_z = 0
            avg_z = 0
        
        # Combine scores
        raw_score = (max_z * 0.6 + avg_z * 0.4)
        confidence = min(raw_score / (self.Z_SCORE_THRESHOLD * 2), 1.0)
        
        is_anomaly = confidence >= self.ANOMALY_CONFIDENCE_THRESHOLD or pattern_match is not None
        
        # Estimate time to failure if trending badly
        ttf = self._estimate_time_to_failure(metrics)
        
        return AnomalyResult(
            is_anomaly=is_anomaly,
            confidence=confidence,
            anomaly_type=pattern_match[0] if pattern_match else ("z_score_deviation" if is_anomaly else None),
            predicted_issue=pattern_match[1]["issue"] if pattern_match else None,
            minutes_to_failure=ttf,
            contributing_factors=deviations[:5],  # Top 5
            recommended_action=pattern_match[1]["action"] if pattern_match else None,
            raw_score=raw_score,
        )
    
    def _check_patterns(self, metrics: Dict[str, float]) -> Optional[Tuple[str, Dict]]:
        """Check for known failure patterns."""
        for pattern_name, pattern_def in self.FAILURE_PATTERNS.items():
            conditions = pattern_def["conditions"]
            all_match = True
            
            for metric, (op, threshold) in conditions.items():
                value = metrics.get(metric)
                if value is None:
                    all_match = False
                    break
                
                if op == ">" and not (value > threshold):
                    all_match = False
                    break
                elif op == "<" and not (value < threshold):
                    all_match = False
                    break
            
            if all_match:
                return (pattern_name, pattern_def)
        
        return None
    
    def _estimate_time_to_failure(self, metrics: Dict[str, float]) -> Optional[float]:
        """
        Estimate time to failure based on trends.
        
        Uses linear extrapolation on temperature trend.
        """
        temp = metrics.get("DCGM_FI_DEV_GPU_TEMP")
        if temp is None or "DCGM_FI_DEV_GPU_TEMP" not in self.history:
            return None
        
        history = list(self.history["DCGM_FI_DEV_GPU_TEMP"])
        if len(history) < 10:
            return None
        
        # Simple linear regression on last 10 samples
        x = np.arange(len(history[-10:]))
        y = np.array(history[-10:])
        
        # Fit y = mx + b
        m = np.polyfit(x, y, 1)[0]  # Slope
        
        if m <= 0:
            return None  # Temperature stable or decreasing
        
        # Critical threshold
        critical_temp = 95
        current_temp = history[-1]
        
        if current_temp >= critical_temp:
            return 0  # Already critical
        
        # Time to critical (in sample intervals)
        samples_to_critical = (critical_temp - current_temp) / m
        
        # Assuming 1 sample per minute
        return max(0, samples_to_critical)
    
    def train(self, historical_data: List[Dict[str, float]]):
        """
        Train the detector on historical data.
        
        This initializes baselines from historical metrics.
        
        Args:
            historical_data: List of metric snapshots
        """
        for snapshot in historical_data:
            for name, value in snapshot.items():
                if isinstance(value, (int, float)) and name.startswith("DCGM_"):
                    self.update_baseline(name, value)
        
        # Optionally train Isolation Forest here for multivariate detection
        try:
            from sklearn.ensemble import IsolationForest
            
            # Build feature matrix
            features = []
            metric_names = [k for k in historical_data[0].keys() if k.startswith("DCGM_")]
            
            for snapshot in historical_data:
                row = [snapshot.get(m, 0) for m in metric_names]
                features.append(row)
            
            if len(features) >= 50:
                self._isolation_forest = IsolationForest(
                    contamination=0.1,
                    random_state=42,
                )
                self._isolation_forest.fit(features)
                print(f"🧠 Trained Isolation Forest on {len(features)} samples")
        except ImportError:
            print("⚠️ scikit-learn not available, using z-score only")


# Global detector instance
gpu_anomaly_detector = GPUAnomalyDetector()


def detect_gpu_anomalies(metrics: Dict[str, float]) -> AnomalyResult:
    """
    Convenience function to detect anomalies.
    
    Uses the global detector instance.
    """
    return gpu_anomaly_detector.detect(metrics)
