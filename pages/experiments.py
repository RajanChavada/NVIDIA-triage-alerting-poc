"""
Experiment Dashboard - A/B Testing & Variant Comparison.

Visualizes:
- Experiment variants and their configurations
- Shadow mode results comparison
- Performance metrics (latency, cost, accuracy)
- Langfuse integration for filtering
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import httpx
import asyncio
from datetime import datetime, timedelta
import random
import os

st.set_page_config(page_title="Experiments", page_icon="🧪", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .experiment-card {
        background-color: #1c2128;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #238636;
        margin-bottom: 15px;
    }
    .variant-control { border-left-color: #238636; }
    .variant-nemotron { border-left-color: #76b900; }
    .variant-simplified { border-left-color: #58a6ff; }
    .metric-improved { color: #238636; }
    .metric-degraded { color: #ff4b4b; }
    .shadow-badge {
        background-color: #6e7681;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8em;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_BASE_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


async def fetch_experiments():
    """Fetch experiments from API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/experiments/", timeout=10.0)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        st.error(f"Failed to fetch experiments: {e}")
    return []


async def fetch_experiment_metrics(experiment_id: str):
    """Fetch metrics for a specific experiment."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_BASE_URL}/experiments/{experiment_id}/metrics",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        st.error(f"Failed to fetch metrics: {e}")
    return {}


async def fetch_experiment_comparison(experiment_id: str):
    """Fetch variant comparison for an experiment."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_BASE_URL}/experiments/{experiment_id}/compare",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        pass
    return {}


def generate_mock_experiment_data():
    """Generate realistic mock data for demonstration."""
    now = datetime.now()
    
    experiments = [
        {
            "experiment_id": "model_comparison_v1",
            "description": "Compare NVIDIA Nemotron vs Claude for triage accuracy",
            "started_at": (now - timedelta(days=7)).isoformat(),
            "variants": ["control", "nemotron"],
            "total_runs": 156,
            "status": "active"
        },
        {
            "experiment_id": "rag_ablation_v1", 
            "description": "Test impact of RAG on triage quality",
            "started_at": (now - timedelta(days=3)).isoformat(),
            "variants": ["control", "simplified_prompt"],
            "total_runs": 82,
            "status": "active"
        }
    ]
    
    # Generate mock metrics per variant
    mock_variant_metrics = {
        "model_comparison_v1": {
            "control": {
                "total_runs": 78,
                "accuracy": 0.82,
                "avg_latency_ms": 4200,
                "avg_cost_usd": 0.0045,
                "avg_tokens": 2800,
                "false_positive_rate": 0.08,
                "is_shadow": False,
            },
            "nemotron": {
                "total_runs": 78,
                "accuracy": 0.79,
                "avg_latency_ms": 2100,
                "avg_cost_usd": 0.0018,
                "avg_tokens": 2400,
                "false_positive_rate": 0.12,
                "is_shadow": True,
            }
        },
        "rag_ablation_v1": {
            "control": {
                "total_runs": 41,
                "accuracy": 0.85,
                "avg_latency_ms": 5100,
                "avg_cost_usd": 0.0052,
                "avg_tokens": 3200,
                "false_positive_rate": 0.05,
                "is_shadow": False,
            },
            "simplified_prompt": {
                "total_runs": 41,
                "accuracy": 0.71,
                "avg_latency_ms": 1800,
                "avg_cost_usd": 0.0015,
                "avg_tokens": 1100,
                "false_positive_rate": 0.18,
                "is_shadow": True,
            }
        }
    }
    
    # Generate time-series data for trends
    time_series = []
    for day in range(7):
        dt = now - timedelta(days=6-day)
        for variant in ["control", "nemotron"]:
            base_latency = 4200 if variant == "control" else 2100
            base_accuracy = 0.82 if variant == "control" else 0.79
            time_series.append({
                "date": dt.strftime("%Y-%m-%d"),
                "variant": variant,
                "latency_ms": base_latency + random.randint(-300, 300),
                "accuracy": base_accuracy + random.uniform(-0.05, 0.05),
                "runs": random.randint(8, 15),
            })
    
    return experiments, mock_variant_metrics, time_series


# Header
st.title("🧪 Experiment Dashboard")
st.caption("A/B Testing & Shadow Mode Analysis for Agent Variants")

# Demo mode toggle in sidebar
st.sidebar.title("🔬 Active Experiments")
use_demo_data = st.sidebar.toggle("🎭 Show Demo Data", value=True, help="Toggle to show mock data for demonstration")

# Fetch data
if use_demo_data:
    experiments, mock_metrics, time_series_data = generate_mock_experiment_data()
    st.sidebar.success("📊 Showing demonstration data")
else:
    experiments = asyncio.run(fetch_experiments())
    mock_metrics = {}
    time_series_data = []
    
    if not experiments:
        st.sidebar.warning("No experiments from API. Toggle demo mode.")
        experiments = []

# Generate mock metrics for fallback
_, all_mock_metrics, all_time_series = generate_mock_experiment_data()

selected_exp_id = None
if experiments:
    selected_exp_id = st.sidebar.selectbox(
        "Select Experiment",
        [exp["experiment_id"] for exp in experiments],
        format_func=lambda x: x.replace("_", " ").title()
    )

selected_exp = next((e for e in experiments if e["experiment_id"] == selected_exp_id), None) if selected_exp_id else None

if selected_exp:
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Description:** {selected_exp.get('description', 'N/A')}")
    st.sidebar.markdown(f"**Variants:** {', '.join(selected_exp.get('variants', []))}")
    st.sidebar.markdown(f"**Total Runs:** {selected_exp.get('total_runs', 0)}")

# Langfuse Integration Section
with st.sidebar.expander("🔗 Langfuse Integration", expanded=False):
    st.markdown("""
    **Available Tags for Filtering:**
    - `experiment:{id}`
    - `variant:{name}`
    - `alert_type:{type}`
    - `service:{name}`
    - `severity:{level}`
    """)
    
    if selected_exp_id and st.button("📋 Copy Langfuse Query"):
        st.code(f'tags:"experiment:{selected_exp_id}"', language="text")
        st.toast("Query copied!")

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.rerun()

# Main Content
if selected_exp:
    # Get metrics for this experiment
    if use_demo_data:
        variant_stats = all_mock_metrics.get(selected_exp_id, {})
        time_series_data = all_time_series
    else:
        comparison = asyncio.run(fetch_experiment_comparison(selected_exp_id))
        variant_stats = comparison.get("variant_stats", {})
        # If no live data, offer to show demo
        if not variant_stats:
            st.info("📊 No experiment runs yet. Enable 'Show Demo Data' in sidebar to see what the dashboard looks like with data.")
            variant_stats = {}
    
    # Experiment Overview
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.header(f"📈 {selected_exp_id.replace('_', ' ').title()}")
        st.caption(selected_exp.get("description", ""))
    
    with col2:
        st.metric("Total Runs", selected_exp.get("total_runs", 0))
    
    with col3:
        status = selected_exp.get("status", "active")
        status_color = "🟢" if status == "active" else "⚪"
        st.metric("Status", f"{status_color} {status.title()}")
    
    st.divider()
    
    # Variant Comparison Cards
    st.subheader("🔀 Variant Comparison")
    
    variant_cols = st.columns(len(variant_stats) if variant_stats else 2)
    
    for idx, (variant_name, stats) in enumerate(variant_stats.items()):
        with variant_cols[idx]:
            is_shadow = stats.get("is_shadow", False)
            shadow_badge = "<span class='shadow-badge'>SHADOW</span>" if is_shadow else ""
            
            # Determine card color based on variant
            card_class = f"variant-{variant_name.split('_')[0]}"
            
            st.markdown(f"""
            <div class="experiment-card {card_class}">
                <h3>{variant_name.replace('_', ' ').title()} {shadow_badge}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Metrics
            st.metric("Accuracy", f"{stats.get('accuracy', 0):.1%}")
            st.metric("Avg Latency", f"{stats.get('avg_latency_ms', 0):.0f}ms")
            st.metric("Avg Cost", f"${stats.get('avg_cost_usd', 0):.4f}")
            st.metric("Avg Tokens", f"{stats.get('avg_tokens', 0):.0f}")
            st.metric("False Positive Rate", f"{stats.get('false_positive_rate', 0):.1%}")
            st.caption(f"Runs: {stats.get('total_runs', 0)}")
    
    st.divider()
    
    # Detailed Charts
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Performance", "💰 Cost Analysis", "📈 Trends", "🔍 Details"])
    
    with tab1:
        st.subheader("Performance Comparison")
        
        if variant_stats:
            # Create comparison bar chart
            metrics_df = pd.DataFrame([
                {"Variant": v, "Metric": "Accuracy (%)", "Value": s.get("accuracy", 0) * 100}
                for v, s in variant_stats.items()
            ] + [
                {"Variant": v, "Metric": "Latency (100ms)", "Value": s.get("avg_latency_ms", 0) / 100}
                for v, s in variant_stats.items()
            ])
            
            fig = px.bar(
                metrics_df,
                x="Variant",
                y="Value",
                color="Metric",
                barmode="group",
                title="Accuracy vs Latency by Variant",
                color_discrete_map={"Accuracy (%)": "#238636", "Latency (100ms)": "#58a6ff"}
            )
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Winner Analysis
            st.subheader("🏆 Winner Analysis")
            
            control_stats = variant_stats.get("control", {})
            other_variants = {k: v for k, v in variant_stats.items() if k != "control"}
            
            for variant_name, stats in other_variants.items():
                col1, col2, col3 = st.columns(3)
                
                acc_diff = (stats.get("accuracy", 0) - control_stats.get("accuracy", 0)) * 100
                latency_diff = control_stats.get("avg_latency_ms", 0) - stats.get("avg_latency_ms", 0)
                cost_diff = (control_stats.get("avg_cost_usd", 0) - stats.get("avg_cost_usd", 0)) * 100
                
                with col1:
                    acc_color = "metric-improved" if acc_diff > 0 else "metric-degraded"
                    st.markdown(f"**Accuracy:** <span class='{acc_color}'>{acc_diff:+.1f}%</span>", unsafe_allow_html=True)
                
                with col2:
                    lat_color = "metric-improved" if latency_diff > 0 else "metric-degraded"
                    st.markdown(f"**Latency:** <span class='{lat_color}'>{latency_diff:+.0f}ms faster</span>", unsafe_allow_html=True)
                
                with col3:
                    cost_color = "metric-improved" if cost_diff > 0 else "metric-degraded"
                    st.markdown(f"**Cost:** <span class='{cost_color}'>{cost_diff:+.2f}% cheaper</span>", unsafe_allow_html=True)
        else:
            st.info("No metrics available yet. Run some experiments to see data.")
    
    with tab2:
        st.subheader("Cost & Token Analysis")
        
        if variant_stats:
            # Cost comparison
            cost_df = pd.DataFrame([
                {"Variant": v, "Cost per Run (USD)": s.get("avg_cost_usd", 0)}
                for v, s in variant_stats.items()
            ])
            
            fig_cost = px.pie(
                cost_df,
                values="Cost per Run (USD)",
                names="Variant",
                title="Cost Distribution by Variant",
                color_discrete_sequence=["#238636", "#76b900", "#58a6ff", "#a371f7"]
            )
            fig_cost.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_cost, use_container_width=True)
            
            # Token usage
            token_df = pd.DataFrame([
                {"Variant": v, "Avg Tokens": s.get("avg_tokens", 0)}
                for v, s in variant_stats.items()
            ])
            
            fig_tokens = px.bar(
                token_df,
                x="Variant",
                y="Avg Tokens",
                title="Average Token Usage by Variant",
                color="Variant",
                color_discrete_sequence=["#238636", "#76b900"]
            )
            fig_tokens.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_tokens, use_container_width=True)
    
    with tab3:
        st.subheader("Performance Trends Over Time")
        
        if use_demo_data and time_series_data:
            ts_df = pd.DataFrame(time_series_data)
            
            # Latency trend
            fig_latency = px.line(
                ts_df,
                x="date",
                y="latency_ms",
                color="variant",
                title="Latency Trend (7 Days)",
                markers=True,
                color_discrete_map={"control": "#238636", "nemotron": "#76b900"}
            )
            fig_latency.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_latency, use_container_width=True)
            
            # Accuracy trend
            fig_accuracy = px.line(
                ts_df,
                x="date",
                y="accuracy",
                color="variant",
                title="Accuracy Trend (7 Days)",
                markers=True,
                color_discrete_map={"control": "#238636", "nemotron": "#76b900"}
            )
            fig_accuracy.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                yaxis_tickformat='.0%'
            )
            st.plotly_chart(fig_accuracy, use_container_width=True)
        else:
            st.info("Trend data requires live experiment runs. Showing demo trends when using mock data.")
    
    with tab4:
        st.subheader("Experiment Configuration")
        
        # Show variant configurations
        for variant_name in selected_exp.get("variants", []):
            with st.expander(f"⚙️ {variant_name.replace('_', ' ').title()} Configuration"):
                if variant_name == "control":
                    st.json({
                        "model_provider": "openrouter",
                        "model_name": "anthropic/claude-3.5-sonnet",
                        "use_rag": True,
                        "confidence_threshold": 0.7,
                        "is_shadow_mode": False
                    })
                elif variant_name == "nemotron":
                    st.json({
                        "model_provider": "nvidia",
                        "model_name": "nvidia/llama-3.1-nemotron-70b-instruct",
                        "use_rag": True,
                        "confidence_threshold": 0.7,
                        "is_shadow_mode": True
                    })
                elif variant_name == "simplified_prompt":
                    st.json({
                        "model_provider": "openrouter",
                        "model_name": "anthropic/claude-3.5-sonnet",
                        "use_rag": False,
                        "prompt_template": "simplified",
                        "confidence_threshold": 0.7,
                        "is_shadow_mode": True
                    })
        
        # Langfuse query examples
        st.subheader("🔗 Langfuse Query Examples")
        st.code(f"""
# Filter by experiment
tags:"experiment:{selected_exp_id}"

# Filter by variant
tags:"variant:control"
tags:"variant:nemotron"

# Combine filters
tags:"experiment:{selected_exp_id}" AND tags:"severity:critical"

# Filter by service
tags:"service:payment-service" AND tags:"experiment:{selected_exp_id}"
        """, language="text")

else:
    st.info("👈 Select an experiment from the sidebar to view details.")

# Footer
st.divider()
st.caption("💡 Tip: Shadow mode variants run in parallel but don't execute actions. Use shadow results to validate before promoting to production.")
