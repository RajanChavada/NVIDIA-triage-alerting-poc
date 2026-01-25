# Langfuse Observability Integration

## Overview

**Langfuse** provides complete audit logging and tracing for your LangGraph workflow. Every LLM call, agent decision, and error is automatically captured.

## How It Works

### 1. **Automatic LLM Tracing**

Every time an agent node calls `get_llm()`, Langfuse automatically logs:
- ✅ **Prompt** sent to the LLM
- ✅ **Response** from the LLM  
- ✅ **Latency** (how long it took)
- ✅ **Token usage** (cost tracking)
- ✅ **Model** used (gemini-2.5-flash, gpt-5.2, etc.)
- ✅ **Timestamp**

### 2. **Trace Grouping**

Each alert triage creates a **trace** with multiple **spans**:

```
Triage Session (e639296f-3e90-454b-b1ff-f7c4d7747400)
├── analyze_logs_auth-service
│   ├── LLM Call (gemini-2.5-flash)
│   └── Response: "As a DevOps engineer..."
├── analyze_metrics_auth-service  
│   ├── LLM Call
│   └── Response: "The metrics show..."
├── incident_rag_auth-service
└── plan_remediation_auth-service
    ├── LLM Call
    └── Response: "Hypothesis: ..."
```

### 3. **Where to View Traces**

🔗 **Langfuse Dashboard**: https://us.cloud.langfuse.com

Login with your credentials (keys in `.env`):
- **Public Key**: `pk-lf-46347486-1a30-4816-a97f-8e949466668e`
- **Secret Key**: `sk-lf-bc3301be-0956-42b5-a060-2b4af6476a70`

### 4. **What You Can Do in Langfuse**

#### **View Individual Traces**
- Click on any trace to see the full conversation
- See exact prompts and responses
- Identify slow LLM calls

#### **Analytics**
- Track which agents are called most
- Monitor LLM costs ($$ per triage)
- See average latency trends

#### **Debugging**
- Filter by service (e.g., all `auth-service` triages)
- Find failed LLM calls
- Compare different alert types

#### **Evaluation**
- Score LLM responses (good/bad)
- Build training datasets
- A/B test different prompts

---

## Configuration

Your current `.env` has:

```bash
LANGFUSE_SECRET_KEY=sk-lf-bc3301be-0956-42b5-a060-2b4af6476a70
LANGFUSE_PUBLIC_KEY=pk-lf-46347486-1a30-4816-a97f-8e949466668e
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
```

Langfuse is **enabled by default** if these keys are present.

---

## Code Flow

### In `app/agents/llm.py`:

```python
def get_llm(trace_name: str = None) -> BaseChatModel:
    llm = ChatOpenAI(...)  # or ChatGoogleGenerativeAI
    
    # Add Langfuse callback
    if settings.langfuse_enabled:
        handler = get_langfuse_handler()
        if handler and trace_name:
            handler.trace_name = trace_name  # Groups related calls
        llm = llm.with_config({"callbacks": [handler]})
    
    return llm
```

### In Agent Nodes (e.g., `analyze_logs.py`):

```python
llm = get_llm(trace_name=f"analyze_logs_{service}")
response = llm.invoke(prompt)  # ← This LLM call is auto-traced to Langfuse
```

---

## Demo Walkthrough

1. **Generate an alert**:
   ```bash
   python -m synthetic.alert_generator
   ```

2. **Open Langfuse**: https://us.cloud.langfuse.com

3. **View the trace**:
   - Navigate to **Traces** tab
   - You'll see a new trace with the alert ID
   - Click to expand and see all LLM calls

4. **Inspect each agent**:
   - Click `analyze_logs_auth-service` to see the log analysis prompt
   - Click `plan_remediation_auth-service` to see the reasoning

5. **Track costs**:
   - Go to **Analytics** → **Token Usage**
   - See $ per triage session

---

## Benefits for Your Demo

### For NVIDIA Stakeholders:

✅ **Transparency**: "Here's exactly what the AI is thinking at each step"  
✅ **Debugging**: "We can trace back any decision to the exact LLM prompt"  
✅ **Cost Control**: "We're tracking $ per incident, currently ~$0.02/triage"  
✅ **Compliance**: "Full audit trail of all AI decisions"  
✅ **Iteration**: "We can A/B test prompts and measure improvement"

---

## Advanced: Manual Tracing

If you want to add custom metadata to traces:

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_host,
)

# Create a trace
trace = langfuse.trace(
    name="alert_triage",
    user_id="system",
    metadata={
        "alert_id": alert_id,
        "service": service,
        "severity": severity,
    }
)

# Add custom spans
span = trace.span(
    name="hypothesis_validation",
    input={"hypothesis": hypothesis},
    output={"validated": True},
)
```

This is already set up automatically for LLM calls via the callback handler!

---

## Troubleshooting

### "No traces appearing in Langfuse"

1. Check your `.env` has the correct keys
2. Restart uvicorn: `Ctrl+C` then `uvicorn app.main:app --reload`
3. Generate a new alert: `python -m synthetic.alert_generator`
4. Wait ~10 seconds, then refresh Langfuse dashboard

### "Traces are empty"

- Langfuse batches uploads every 10-30 seconds
- Try `langfuse.flush()` to force immediate upload (for testing)

### "Too many traces"

- Filter by date or service in the Langfuse UI
- Archive old traces

---

## Next Steps

- [ ] Add custom scoring to evaluate LLM responses
- [ ] Set up Langfuse alerts for anomalies (e.g., >5s latency)
- [ ] Create dashboards for stakeholder demos
- [ ] Export traces for compliance audits
