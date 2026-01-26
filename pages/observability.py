"""
Observability Dashboard - Token usage, latency, cost analysis.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import httpx

st.set_page_config(page_title="Observability", page_icon="📊", layout="wide")
st.title("📊 Agent Observability Dashboard")
st.caption("Monitor token usage, latency, and costs across triage workflows")

import os

# API Configuration
API_BASE_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

# Fetch metrics
try:
    response = httpx.get(f"{API_BASE_URL}/observability/metrics", timeout=5.0)
    all_metrics = response.json() if response.status_code == 200 else []
except Exception as e:
    st.error(f"⚠️ Could not fetch metrics: {e}")
    all_metrics = []

if not all_metrics:
    st.info("⏳ No metrics available yet - metrics will appear once we instrument the agent nodes!")
    st.markdown("""
    **What's happening:**
    - We've set up the observability infrastructure ✅
    - API endpoint is working ✅  
    - We still need to instrument each agent node to capture:
        - Token usage per LLM call
        - Latency per node
        - Cost estimation
    
    **Next step:** Instrument the agent nodes to populate this dashboard!
    """)
    st.stop()

# Build DataFrame from metrics
df_list = []
for triage in all_metrics:
    for node in triage.get("node_metrics", []):
        df_list.append({
            "service": triage["service"],
            "node": node["node_name"],
            "duration_ms": node.get("duration_ms", 0),
            "tokens": node.get("total_tokens", 0),
            "cost_usd": node.get("cost_usd", 0.0),
            "model": node.get("llm_model", "N/A"),
        })

if not df_list:
    st.warning("📊 Metrics captured but no node-level data yet. Instrument nodes to see details!")
    st.stop()

df = pd.DataFrame(df_list)

# Summary metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Triages", len(all_metrics))

with col2:
    total_tokens = df["tokens"].sum() if "tokens" in df.columns else 0
    st.metric("Total Tokens", f"{int(total_tokens):,}")

with col3:
    total_cost = df["cost_usd"].sum() if "cost_usd" in df.columns else 0
    st.metric("Total Cost", f"${total_cost:.4f}")

with col4:
    avg_duration = df["duration_ms"].mean() if "duration_ms" in df.columns and len(df) > 0 else 0
    st.metric("Avg Node Duration", f"{avg_duration:.0f}ms")

st.divider()

# Charts
tab1, tab2, tab3 = st.tabs(["📊 Token Usage", "⏱️ Latency", "💰 Cost"])

with tab1:
    st.subheader("Token Usage by Node")
    if "tokens" in df.columns and df["tokens"].sum() > 0:
        fig = px.bar(
            df.groupby("node")["tokens"].sum().reset_index(),
            x="node",
            y="tokens",
            title="Total Tokens per Agent Node"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No token data captured yet")

with tab2:
    st.subheader("Latency by Node")
    if "duration_ms" in df.columns and len(df) > 0:
        fig = px.bar(
            df.groupby("node")["duration_ms"].mean().reset_index(),
            x="node",
            y="duration_ms",
            title="Average Duration per Agent Node (ms)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No latency data captured yet")

with tab3:
    st.subheader("Cost Breakdown")
    if "cost_usd" in df.columns and df["cost_usd"].sum() > 0:
        fig = px.pie(
            df.groupby("node")["cost_usd"].sum().reset_index(),
            values="cost_usd",
            names="node",
            title="Cost Distribution by Node"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No cost data captured yet")

# Raw data
with st.expander("📋 Raw Metrics Data"):
    st.json(all_metrics)
