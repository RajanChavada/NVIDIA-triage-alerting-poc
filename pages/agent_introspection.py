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
Monitors DCGM metrics via Prometheus (15s scrape).

**Key Metrics:** dcgm_gpu_ecc_errors_total, dcgm_gpu_temp, dcgm_memory_bandwidth

**Example Output Commands:**
```bash
curl -G 'http://prometheus:9090/api/v1/query' --data-urlencode 'query=rate(dcgm_gpu_ecc_errors_total[5m])'
kubectl get events --field-selector involvedObject.name=gpu-node-47
```""",
        "examples": "Provides copy-paste Prometheus queries and kubectl commands for diagnosing ECC errors."
    },
    {
        "name": "SRE Diagnostic Agent",
        "node": "analyze_logs",
        "description": "Interprets log patterns, DCGM health checks, and correlates them with hardware diagnostics.",
        "role": "Log Investigator / Root Cause Analyst",
        "tools": ["search_logs"],
        "context": """You are an NVIDIA Cluster SRE Agent.
Use ChatOps patterns (/sre diagnose).

**Key Patterns:** DCGM health failures, XID errors, stack traces

**Example Output Commands:**
```bash
ssh bastion -t 'ssh gpu-node-47 nvidia-smi -q'
kubectl logs -l app=dcgm-exporter --since=1h | grep -i 'xid'
```""",
        "examples": "Provides nvidia-smi and dcgmi commands to diagnose XID 79 GPU failures."
    },
    {
        "name": "Incident RAG Agent",
        "node": "incident_rag",
        "description": "Retrieves similar historical incidents from the incident database to suggest known resolutions.",
        "role": "Historical Knowledge Base",
        "tools": ["VectorDB Search (Mock)"],
        "context": """Compare current symptoms to historical incident vectors.

**Example Signatures:**
'ECC errors + temp spike + restart loop' = hardware_degradation (0.94 match)

Suggests resolutions from past incidents like INC-1847.""",
        "examples": "Notes that INC-1847 was resolved by decommissioning the node due to similar ECC signatures."
    },
    {
        "name": "Lead Engineer Agent",
        "node": "plan_remediation",
        "description": "Synthesizes all gathered data to propose a final remediation strategy through the GitOps/ChatOps lifecycle.",
        "role": "Decision Maker / Workflow Orchestrator",
        "tools": ["kubectl", "Ansible/Terraform (via ChatOps)"],
        "context": """You are an NVIDIA Cluster Lead Engineer.
NVIDIA Remediation Workflows: kubectl drain, /sre remediate

**Example Remediation Commands:**
```bash
kubectl cordon gpu-node-47
kubectl drain gpu-node-47 --ignore-daemonsets --grace-period=300
# Slack: /sre remediate gpu-node-47 --action=decommission
```""",
        "examples": "Provides full kubectl drain and ChatOps command sequence for node decommissioning."
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

st.subheader("🚀 The Triage Flow (ReAct Agent Architecture)")
import graphviz
dot = graphviz.Digraph()
dot.attr(rankdir='TB', bgcolor='transparent')
dot.attr('node', shape='box', style='filled,rounded', fontname='Arial', fontsize='11', fillcolor='#1f6feb', fontcolor='white')
dot.attr('edge', color='#58a6ff', penwidth='2')

# Nodes matching graph.py
dot.node('START', 'START', fillcolor='#238636')
dot.node('gather', 'gather_context', fillcolor='#1f6feb')
dot.node('logs', 'analyze_logs', fillcolor='#8957e5')
dot.node('metrics', 'analyze_metrics', fillcolor='#8957e5')
dot.node('tools', 'tools', fillcolor='#0969da')
dot.node('rag', 'incident_rag', fillcolor='#0969da')
dot.node('plan', 'plan_remediation', fillcolor='#bf4b00')
dot.node('validate', 'validate_action', fillcolor='#a371f7')
dot.node('finalize', 'finalize', fillcolor='#238636')

# Edges matching graph.py (including ReAct loops)
dot.edge('START', 'gather')
dot.edge('gather', 'logs')
dot.edge('logs', 'tools', label='tool call')
dot.edge('tools', 'logs', label='search_logs')
dot.edge('logs', 'metrics', label='next')
dot.edge('metrics', 'tools', label='tool call')
dot.edge('tools', 'metrics', label='get_metrics')
dot.edge('metrics', 'rag', label='next')
dot.edge('rag', 'plan')
dot.edge('plan', 'validate')
dot.edge('validate', 'finalize')

st.graphviz_chart(dot)

st.caption("Custom built for NVIDIA SRE Demo")
