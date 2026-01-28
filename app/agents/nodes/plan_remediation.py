from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AlertTriageState, create_event
from app.agents.llm import get_llm, MetricsTracker
import re


async def plan_remediation(state: AlertTriageState) -> dict:
    """Generate remediation plan based on all gathered evidence."""
    alert = state["alert"]
    service = alert.get("service", "unknown")
    triage_id = str(state.get("triage_id", "unknown"))
    
    with MetricsTracker(triage_id, "plan_remediation") as tracker:
        try:
            llm = get_llm()
            
            system_prompt = SystemMessage(content=f"""You are an NVIDIA Cluster Lead Engineer.
Synthesize all logs, metrics, and past incidents discussed in the conversation.
Identify the root cause and propose a specific remediation plan for {service}.
NVIDIA Remediation Workflows:
- Node Draining: `kubectl drain` (cordon node, evict pods with graceful timeout).
- ChatOps: `/sre remediate` triggers Ansible/Terraform lifecycle.
- Lifecycle: Drains node, labels as 'decommissioned', Terraform provisions replacement from spares, then rebalance.""")
            
            prompt = """Provide your final analysis:
1. **Hypothesis**: What is the root cause?
2. **Recommended Action**: What is the fix?
3. **Confidence Level**: Scale of 0-1 (e.g., 0.85)"""
            
            messages = [system_prompt] + state.get("messages", []) + [HumanMessage(content=prompt)]
            response = llm.invoke(messages)
            tracker.track_tokens(str(messages), response.content)
            
            llm_reasoning = response.content
            
            # More robust parsing for multi-line sections
            def extract_section(text, section_keywords, next_keywords=None):
                pattern = f"(?:{'|'.join(section_keywords)}).*?:\\s*(.*?)(?=\\n(?:{'|'.join(next_keywords)})|$)" if next_keywords else f"(?:{'|'.join(section_keywords)}).*?:\\s*(.*)"
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                return match.group(1).strip() if match else None

            hypothesis = extract_section(llm_reasoning, ["Hypothesis", "Root Cause"], ["Recommended Action", "Action", "Confidence"])
            action = extract_section(llm_reasoning, ["Recommended Action", "Action"], ["Confidence"])
            
            # Fallbacks
            if not hypothesis:
                hypothesis = "Investigating Root Cause"
            if not action:
                action = "Manual intervention required"
            
            confidence_match = re.search(r'(?:Confidence).*?:\s*([0-9.]+)', llm_reasoning, re.IGNORECASE)
            try:
                confidence = float(confidence_match.group(1)) if confidence_match else 0.8
            except:
                confidence = 0.8
            
        except Exception as e:
            llm_reasoning = f"Planning failed: {e}"
            hypothesis = "Degraded Service"
            action = f"Restart {service}"
            confidence = 0.5
            response = HumanMessage(content=llm_reasoning)
    
    return {
        "hypothesis": hypothesis,
        "recommended_action": action,
        "confidence": confidence,
        "messages": [response],
        "events": [create_event("plan_remediation", f"Proposed: {action[:100]}", llm_reasoning=llm_reasoning)],
    }
