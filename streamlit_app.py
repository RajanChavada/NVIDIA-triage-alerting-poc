import streamlit as st
import pandas as pd
import httpx
import asyncio
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import graphviz

# Set page config
st.set_page_config(
    page_title="NVIDIA Triage AI | Global Testing Laboratory",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #238636;
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: #2ea043;
        border: none;
    }
    .severity-critical { color: #ff4b4b; font-weight: bold; }
    .severity-high { color: #ff9f1a; font-weight: bold; }
    .severity-medium { color: #e9c46a; font-weight: bold; }
    .severity-low { color: #2a9d8f; font-weight: bold; }
    
    .status-badge {
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8em;
    }
    .trace-node {
        background-color: #1c2128;
        padding: 10px;
        border-radius: 8px;
        border-left: 4px solid #58a6ff;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

import os

# API Configuration
# Use environment variable for backend URL if provided, otherwise default to localhost
API_BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

def create_workflow_graph():
    """Create a visual representation of the LangGraph workflow."""
    graph = graphviz.Digraph()
    graph.attr(rankdir='TB', bgcolor='transparent')
    graph.attr('node', shape='box', style='filled,rounded', fontname='Arial', fontsize='11')
    graph.attr('edge', color='#58a6ff', penwidth='2')
    
    # Define nodes with colors
    nodes = [
        ('START', '#238636'),
        ('gather_context', '#1f6feb'),
        ('analyze_logs', '#8957e5'),
        ('analyze_metrics', '#8957e5'),
        ('tools', '#0969da'),
        ('incident_rag', '#0969da'),
        ('plan_remediation', '#bf4b00'),
        ('validate_action', '#a371f7'),
        ('finalize', '#238636'),
    ]
    
    for node, color in nodes:
        graph.node(node, node.replace('_', '\n'), fillcolor=color, fontcolor='white')
    
    # Define edges
    edges = [
        ('START', 'gather_context'),
        ('gather_context', 'analyze_logs'),
        ('analyze_logs', 'tools'),
        ('tools', 'analyze_logs'),
        ('analyze_logs', 'analyze_metrics'),
        ('analyze_metrics', 'tools'),
        ('tools', 'analyze_metrics'),
        ('analyze_metrics', 'incident_rag'),
        ('incident_rag', 'plan_remediation'),
        ('plan_remediation', 'validate_action'),
        ('validate_action', 'finalize'),
    ]
    
    graph.edges(edges)
    return graph

async def get_triage_results():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/alerts/triage")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []

async def approve_action(triage_id):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{API_BASE_URL}/alerts/triage/{triage_id}/approve")
            return response.json()
        except Exception as e:
            return {"error": str(e)}

async def reject_action(triage_id):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{API_BASE_URL}/alerts/triage/{triage_id}/reject")
            return response.json()
        except Exception as e:
            return {"error": str(e)}

async def trigger_synthetic_alert(service_name=None, alert_type=None):
    async with httpx.AsyncClient() as client:
        try:
            params = {}
            if service_name: params["service_name"] = service_name
            if alert_type: params["alert_type"] = alert_type
            response = await client.post(f"{API_BASE_URL}/alerts/generate", params=params)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

# Sidebar - Real-time Feed
st.sidebar.title("🚨 Recent Alerts")

# Demo Controls
with st.sidebar.expander("🚀 Demo Scenarios", expanded=True):
    scenario = st.selectbox("Select Failure Mode", [
        "Random", "latency_spike", "error_rate_spike", "cpu_anomaly", "memory_anomaly"
    ])
    
    st.write("Trigger Service:")
    col1, col2 = st.columns(2)
    if col1.button("🔐 Auth"):
        asyncio.run(trigger_synthetic_alert("auth-service", scenario if scenario != "Random" else None))
        st.toast("Auth Alert Triggered!")
        time.sleep(1)
        st.rerun()
    if col2.button("💳 Payment"):
        asyncio.run(trigger_synthetic_alert("payment-service", scenario if scenario != "Random" else None))
        st.toast("Payment Alert Triggered!")
        time.sleep(1)
        st.rerun()
    if st.button("👥 User Service", use_container_width=True):
        asyncio.run(trigger_synthetic_alert("user-service", scenario if scenario != "Random" else None))
        st.toast("User Alert Triggered!")
        time.sleep(1)
        st.rerun()

if st.sidebar.button("🔄 Refresh Alerts", use_container_width=True):
    st.rerun()

results = asyncio.run(get_triage_results())

if not results:
    st.sidebar.info("No active alerts being triaged.")
    selected_triage = None
else:
    # Sort for display
    results = sorted(results, key=lambda x: str(x.get('triage_id', '')), reverse=True)
    
    for res in results:
        t_id = res['triage_id']
        service = res['service']
        severity = res['severity']
        
        # Display clickable alert item
        with st.sidebar.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                # Highlight if selected
                is_selected = "selected_triage_id" in st.session_state and st.session_state.selected_triage_id == t_id
                btn_label = f"**{service}**" if is_selected else f"{service}"
                if st.button(f"{btn_label} | {severity.upper()}", key=f"btn_{t_id}"):
                    st.session_state.selected_triage_id = t_id
            with col2:
                st.markdown(f"<span class='severity-{severity.lower()}'>•</span>", unsafe_allow_html=True)

# Main Dashboard Container
if "selected_triage_id" in st.session_state:
    selected_res = next((r for r in results if r['triage_id'] == st.session_state.selected_triage_id), None)
else:
    selected_res = results[0] if results else None

if selected_res:
    st.title(f"🔍 Triage Analysis: {selected_res['service']}")
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Overview", "🧠 Agent Workflow", "📄 Raw Data"])
    
    with tab1:
        col_main, col_side = st.columns([2, 1])
        
        with col_main:
            # Metrics Visualization
            st.subheader("� Metric Anomalies")
            
            # Create dummy time series with spike
            times = pd.date_range(end=datetime.now(), periods=20, freq='1min')
            values = [100 + (i*2 if i < 15 else 500 if i == 15 else 150) for i in range(20)]
            df = pd.DataFrame({'Time': times, 'Latency (ms)': values})
            
            fig = px.line(df, x='Time', y='Latency (ms)', title='Latency Window (p95)')
            fig.add_hline(y=120, line_dash="dash", annotation_text="Baseline", line_color="green")
            fig.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
            # Key Findings
            st.subheader("🔍 Key Findings")
            col1, col2, col3, col4 = st.columns(4)
            
            tool_call_count = sum(len(event.get('tool_calls', [])) for event in selected_res.get('events', []))
            
            with col1:
                st.metric("Anomalies Detected", len(selected_res.get('anomalies', [])))
            with col2:
                st.metric("Similar Incidents", len(selected_res.get('similar_incidents', [])))
            with col3:
                st.metric("Data Queries", tool_call_count)
            with col4:
                st.metric("Processing Steps", len(selected_res.get('events', [])))

        with col_side:
            # Remediation Panel
            st.subheader("🛠️ Recommended Action")
            st.info(f"**Hypothesis:** {selected_res.get('hypothesis', 'Analyzing...')}")
            
            st.warning(f"**Action:** {selected_res.get('recommended_action', 'Pending decision')}")
            
            confidence = selected_res.get('confidence', 0)
            st.metric("Confidence", f"{confidence:.0%}")
            
            st.write("---")
            if selected_res['status'] == 'pending':
                if st.button("✅ Approve & Execute"):
                    resp = asyncio.run(approve_action(selected_res['triage_id']))
                    st.success(resp.get("message", "Action approved"))
                    time.sleep(1)
                    st.rerun()
                
                if st.button("❌ Reject Action"):
                    resp = asyncio.run(reject_action(selected_res['triage_id']))
                    st.error(resp.get("reason", "Action rejected"))
                    time.sleep(1)
                    st.rerun()
            else:
                st.success(f"Status: **{selected_res['status'].upper()}**")
    
    with tab2:
        col_graph, col_trace = st.columns([1, 1])
        
        with col_graph:
            st.subheader("🔄 LangGraph Workflow Structure")
            st.caption("Nodes represent specialized agents in the triage pipeline")
            
            # Display workflow graph
            workflow_graph = create_workflow_graph()
            st.graphviz_chart(workflow_graph)
        
        with col_trace:
            st.subheader("🧠 Agent Reasoning Trace")
            st.caption("Expand each node to see detailed outputs")
            
            # Interactive trace with expanders
            events = selected_res.get('events', [])
            for i, event in enumerate(events):
                node_name = event.get('node', 'unknown')
                summary = event.get('summary', '')
                
                # Color code based on node type
                if 'error' in node_name.lower():
                    icon = "❌"
                    color = "#ff4b4b"
                elif node_name == "finalize":
                    icon = "✅"
                    color = "#238636"
                elif "analyze" in node_name:
                    icon = "🔬"
                    color = "#8957e5"
                elif "plan" in node_name:
                    icon = "💡"
                    color = "#bf4b00"
                elif node_name == "tools":
                    icon = "🛠️"
                    color = "#0969da"
                else:
                    icon = "⚙️"
                    color = "#1f6feb"
                
                with st.expander(f"{icon} **{node_name.upper()}** - Step {i+1}/{len(events)}", expanded=(i == len(events) - 1)):
                    st.markdown(f"**Summary:** {summary}")
                    
                    # Show tool calls if present
                    if 'tool_calls' in event and event['tool_calls']:
                        st.markdown("**🛠️ Tool Calls Requested:**")
                        for tc in event['tool_calls']:
                            st.code(f"{tc['name']}({tc.get('args', {})})")
                    
                    # Show LLM reasoning if available
                    if 'llm_reasoning' in event and event['llm_reasoning']:
                        st.markdown("---")
                        st.markdown("**🤖 Agent Thinking:**")
                        st.markdown(event['llm_reasoning'])
                        st.markdown("---")
                    
                    # Show additional metadata
                    meta_cols = st.columns(2)
                    with meta_cols[0]:
                        if 'service' in event: st.write(f"🏢 Service: {event['service']}")
                        if 'status' in event: st.write(f"📌 Status: {event['status']}")
                    with meta_cols[1]:
                        if 'confidence' in event: st.write(f"🎯 Confidence: {event['confidence']:.0%}")
                    
                    st.caption(f"🕒 {event.get('ts', 'N/A')}")
    
    with tab3:
        # Raw Alert Payload
        st.subheader("📄 Full Triage Result JSON")
        st.json(selected_res)

else:
    st.info("👈 Select an alert from the sidebar to view triage details.")
    # Show a premium landing state
    st.image("https://www.nvidia.com/content/dam/en-zz/Solutions/deep-learning/deep-learning-education/nvidia-training-logo-625x352.png", width=200)
    st.header("Welcome to AI Triage Console")
    st.write("This Agentic AI workflow is currently monitoring 3 microservices.")

# Auto-refresh logic (optional for demo)
# st.empty()
# time.sleep(5)
# st.rerun()
