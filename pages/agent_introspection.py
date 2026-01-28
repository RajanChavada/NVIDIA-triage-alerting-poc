import streamlit as st
import os

st.set_page_config(page_title="Agent Introspection", page_icon="🤖", layout="wide")

# Custom CSS for a premium look
st.markdown("""
<style>
    .agent-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
    }
    .agent-header {
        color: #76B900; /* NVIDIA Green */
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .status-badge {
        background-color: #76B900;
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 12px;
        float: right;
    }
    .tool-tag {
        background-color: #444;
        color: #ddd;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 14px;
        margin-right: 5px;
        display: inline-block;
        margin-top: 5px;
    }
    .code-block {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 15px;
        border-radius: 8px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 14px;
        overflow-x: auto;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Agent Introspection & Context Engineering")
st.markdown("""
This page provides a deep dive into the **Enriched Core Agents** powering the NVIDIA Triage POC. 
Understand the specific context engineering, personas, and tools available to each agent in the workflow.
""")

# Agent Data
agents = [
    {
        "name": "Observability Agent",
        "node": "analyze_metrics",
        "description": "Analyzes GPU-specific metrics and identifies anomalies in the Prometheus pull-based streams.",
        "role": "Metric Specialist / Anomaly Detector",
        "tools": ["get_service_metrics"],
        "context": """You are an NVIDIA Cluster Observability Agent.
Your job is to analyze metrics for the service.
NVIDIA uses a pull-based Prometheus system (15s scrape interval) collecting DCGM metrics.
Key metrics to monitor:
- dcgm_gpu_ecc_errors_total (Check for rate change > 0)
- dcgm_gpu_temp (Check for spikes > 80C)
- dcgm_memory_bandwidth (Check for utilization anomalies)
Look for CPU spikes, memory leaks, GPU thermal throttling, or ECC error increases.""",
        "examples": "Identifies that a 94% match to historical memory defects exists when ECC errors spike alongside temperature deltas."
    },
    {
        "name": "SRE Diagnostic Agent",
        "node": "analyze_logs",
        "description": "Interprets log patterns, DCGM health checks, and correlates them with hardware diagnostics.",
        "role": "Log Investigator / Root Cause Analyst",
        "tools": ["search_logs"],
        "context": """You are an NVIDIA Cluster SRE Agent.
Your job is to analyze logs for the service.
Use diagnostic patterns from ChatOps (e.g., `/sre diagnose`).
Look for:
- DCGM health check failures
- `nvidia-smi` output anomalies
- Stack traces, segmentation faults, or GPU driver ECC errors.""",
        "examples": "Detects 'XID 79: GPU has fallen off the bus' patterns in system logs during high workloads."
    },
    {
        "name": "Incident RAG Agent",
        "node": "incident_rag",
        "description": "Retrieves similar historical incidents from the incident database to suggest known resolutions.",
        "role": "Historical Knowledge Base",
        "tools": ["VectorDB Search (Mock)"],
        "context": """Compare current evidence (ECC errors, temp spikes) to the current context.
Look for pattern matches in historical incidents stored as feature vectors.
Example Signatures:
'ECC errors + temp spike + restart loop' = hardware_degradation (0.94 confidence).""",
        "examples": "Notes that INC-1847 was resolved by decommissioning the node due to similar ECC signatures."
    },
    {
        "name": "Lead Engineer Agent",
        "node": "plan_remediation",
        "description": "Synthesizes all gathered data to propose a final remediation strategy through the GitOps/ChatOps lifecycle.",
        "role": "Decision Maker / Workflow Orchestrator",
        "tools": ["kubectl", "Ansible/Terraform (via ChatOps)"],
        "context": """You are an NVIDIA Cluster Lead Engineer.
Synthesize all logs, metrics, and past incidents.
NVIDIA Remediation Workflows:
- Node Draining: `kubectl drain` (cordon node, evict pods with graceful timeout).
- ChatOps: `/sre remediate` triggers Ansible/Terraform lifecycle.
- Lifecycle: Drains node, labels as 'decommissioned', Terraform provisions replacement from spares, then rebalance.""",
        "examples": "Decides to decommission node-47 based on high confidence of hardware failure, triggering an automated replacement pipeline."
    }
]

# Tabs for each agent
agent_tabs = st.tabs([a["name"] for a in agents])

for i, agent in enumerate(agents):
    with agent_tabs[i]:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown(f"### {agent['name']}")
            st.info(f"**Role:** {agent['role']}")
            st.write(agent['description'])
            
            st.markdown("#### 🛠️ Available Tools")
            for tool in agent['tools']:
                st.markdown(f"<span class='tool-tag'>{tool}</span>", unsafe_allow_html=True)
            
            st.markdown("#### 💡 Example Action")
            st.write(agent['examples'])

        with col2:
            st.markdown("#### 📜 Enriched System Context")
            st.markdown(f"<div class='code-block'>{agent['context']}</div>", unsafe_allow_html=True)
            
            with st.expander("View Node Lifecycle"):
                st.markdown(f"""
                - **Node ID:** `{agent['node']}`
                - **Execution:** Async
                - **State Sync:** LangGraph State Management
                - **Observability:** Token tracking & Latency logging enabled
                """)

st.divider()

st.subheader("🚀 The Triage Flow (Enriched)")
import graphviz
dot = graphviz.Digraph()
dot.attr(rankdir='LR', bgcolor='transparent')
dot.attr('node', shape='box', style='filled,rounded', fontname='Arial', fontsize='11', fillcolor='#1f6feb', fontcolor='white')
dot.attr('edge', color='#58a6ff', penwidth='2')

dot.node('A', 'Alert Triggered', fillcolor='#238636')
dot.node('B', 'Observability Agent')
dot.node('C', 'SRE Diagnostic Agent')
dot.node('D', 'Incident RAG Agent')
dot.node('E', 'Lead Engineer Agent')
dot.node('F', 'Automated Remediation', fillcolor='#bf4b00')

dot.edge('A', 'B')
dot.edge('B', 'C')
dot.edge('C', 'D')
dot.edge('D', 'E')
dot.edge('E', 'F')

st.graphviz_chart(dot)

st.caption("Custom built for NVIDIA SRE Demo")
