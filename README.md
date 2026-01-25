# NVIDIA Triage Alerting MVP

AI-powered triage alerting system using multi-agent workflows for infrastructure automation.

## 🎯 Overview

This POC demonstrates intelligent automation for infrastructure alert handling:

- **Provider-Agnostic LLM**: Swap between Gemini and OpenRouter via environment config
- **Event-Driven Architecture**: asyncio.Queue for MVP (Kafka-ready design for production)
- **Multi-Agent Workflow**: LangGraph orchestrating specialized agents
- **Observability**: Langfuse integration for tracing and evaluation

## 🏗️ Architecture

```
DATA SOURCES          INGESTION & DETECTION       LANGGRAPH WORKFLOW           OUTPUT
┌─────────────┐      ┌──────────────────┐      ┌─────────────────────┐     ┌──────────────┐
│ Auth Service├──┐   │ Metrics Scraper  │      │    gather_context   │     │   Postgres   │
│ Payment Svc │──┼──>│ Anomaly Detector ├─────>│         │           │────>│  (Results)   │
│ User Service│──┘   │ Alert Generator  │      │  analyze_logs ║     │     └──────────────┘
└─────────────┘      └──────────────────┘      │  analyze_metrics    │     ┌──────────────┐
                              │                │         │           │     │  Streamlit   │
                     ┌────────▼────────┐       │   incident_rag      │────>│  Dashboard   │
                     │    FastAPI      │       │         │           │     └──────────────┘
                     │ POST /triage    │──────>│ plan_remediation    │
                     └─────────────────┘       │ validate_action     │
                                               │     finalize        │
                                               └─────────────────────┘
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone and navigate
cd NVIDIA-triage-alerting-poc

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start Infrastructure (Optional)

If you have Docker installed, you can start Postgres and Redis:
```bash
docker-compose up -d
```
**Note:** If Docker is not installed, the app will currently use its in-memory queue and store for the MVP demo.

### 3. Run the API

```bash
# Start FastAPI server
uvicorn app.main:app --reload
```

### 4. Run the Streamlit Dashboard (New Window)

```bash
# Start the UI
streamlit run streamlit_app.py
```

### 5. Test End-to-End (New Window)

```bash
# Run the demo script to generate fake alerts
python -m synthetic.alert_generator
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/alerts/triage` | Submit alert for triage |
| GET | `/alerts/triage/{id}` | Get triage result |
| GET | `/alerts/triage` | List all triage results |
| POST | `/alerts/triage/{id}/approve` | Approve recommended action |
| POST | `/alerts/triage/{id}/reject` | Reject with feedback |
| GET | `/health` | Health check |

### Example Request

```bash
curl -X POST http://localhost:8000/alerts/triage \
  -H "Content-Type: application/json" \
  -d '{
    "service": "auth-service",
    "severity": "critical",
    "alert_type": "latency_spike",
    "detector": "threshold",
    "timestamp": "2026-01-24T19:20:10Z",
    "metric_snapshot": {
      "latency_p95_ms": 800,
      "latency_baseline_ms": 120
    },
    "context": {
      "recent_log_ids": ["log-001"],
      "region": "us-central1"
    }
  }'
```

## 🤖 LangGraph Workflow

The triage workflow uses specialized agents:

1. **gather_context** - Fetch logs and metrics around alert
2. **analyze_logs** - LLM analysis of error patterns
3. **analyze_metrics** - Z-score anomaly detection
4. **incident_rag** - Vector search for similar past incidents
5. **plan_remediation** - Propose action with confidence
6. **validate_action** - Safety checks and blast radius
7. **finalize** - Store result and complete

```bash
# Visualize the graph
python -c "from app.agents.graph import visualize_graph; print(visualize_graph())"
```

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | LLM provider: `gemini` or `openrouter` |
| `GOOGLE_API_KEY` | - | Gemini API key |
| `OPENROUTER_API_KEY` | - | OpenRouter API key |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Postgres connection |
| `LANGFUSE_PUBLIC_KEY` | - | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | - | Langfuse secret key |

## 📊 Metrics & Anomaly Detection

For metrics analysis, we use **z-score based anomaly detection** over a sliding window:

```python
z_score = (current_value - baseline) / (baseline * std_factor)
if z_score > threshold:
    anomaly_detected = True
```

> In production at NVIDIA, you might replace this with Prometheus recording rules or ML-based detectors.

## 🛡️ Safety & Validation

The validate_action node enforces:

- **White-list**: Only approved actions (scale, restart, rate-limit)
- **Critical services**: Always require human approval
- **Confidence thresholds**: Auto-approve only high-confidence + low-severity
- **Blast radius**: Assess potential impact before execution

## 📁 Project Structure

```
NVIDIA-triage-alerting-poc/
├── app/
│   ├── main.py           # FastAPI entry point
│   ├── config.py         # Provider-agnostic config
│   ├── models/           # Pydantic + SQLAlchemy models
│   ├── api/routes/       # API endpoints
│   ├── services/         # Triage queue service
│   └── agents/           # LangGraph workflow
│       ├── state.py      # AlertTriageState
│       ├── graph.py      # Workflow definition
│       ├── llm.py        # LLM configuration
│       └── nodes/        # Agent implementations
├── synthetic/            # Demo harness
│   ├── services.yaml     # Service registry
│   └── alert_generator.py # E2E demo script
├── docker-compose.yml
└── requirements.txt
```

## 🔮 Future Enhancements

- [ ] **Kafka Integration**: Replace asyncio.Queue for production scale
- [ ] **Streamlit Dashboard**: Real-time alert feed and trace visualization
- [ ] **Chroma/pgvector**: Real incident embeddings for RAG
- [ ] **Prometheus Integration**: Actual metrics from /metrics endpoints
- [ ] **Action Execution**: Real remediation (scale, restart) via K8s API

## 📜 License

MIT License - See [LICENSE](LICENSE)