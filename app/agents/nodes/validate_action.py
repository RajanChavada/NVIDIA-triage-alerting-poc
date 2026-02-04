"""
Validate Action Node - Uses NeMo-style guardrails to validate remediation safety.

Integrates:
- TriageGuardrails.validate_action() for high-risk action detection
- TriageGuardrails.redact_pii() for log sanitization
- LLM-based safety assessment for nuanced analysis
"""
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AlertTriageState, create_event
from app.agents.llm import get_llm, MetricsTracker
from app.agents.guardrails import TriageGuardrails


async def validate_action(state: AlertTriageState) -> dict:
    """
    Validate the proposed remediation action using NeMo-style guardrails.
    
    Validation layers:
    1. TriageGuardrails.validate_action() - Rule-based high-risk detection
    2. LLM safety assessment - Nuanced analysis for edge cases
    3. PII redaction - Sanitize action text before logging
    """
    action = state.get("recommended_action", "No action")
    service = state.get("alert", {}).get("service", "unknown")
    severity = state.get("alert", {}).get("severity", "unknown")
    confidence = state.get("confidence", 0.0)
    triage_id = str(state.get("triage_id", "unknown"))
    
    with MetricsTracker(triage_id, "validate_action") as tracker:
        try:
            # === Layer 1: Rule-based Guardrails ===
            # Check for high-risk actions, critical services, and low confidence
            guardrail_result = TriageGuardrails.validate_action(action, service, confidence)
            
            # Sanitize action text (redact PII before logging/display)
            sanitized_action = TriageGuardrails.redact_pii(action)
            
            # If guardrails block the action, require approval immediately
            if not guardrail_result["allowed"]:
                return {
                    "requires_approval": True,
                    "events": [create_event(
                        "validate_action",
                        f"🛡️ Guardrails triggered: {guardrail_result['reason']}",
                        guardrail_blocked=True,
                        guardrail_reason=guardrail_result["reason"],
                        sanitized_action=sanitized_action,
                    )],
                }
            
            # === Layer 2: LLM Safety Assessment ===
            llm = get_llm()
            
            system_prompt = SystemMessage(content=f"""You are an NVIDIA Cluster Security & Reliability Guardrail.
Assess the risk of the proposed action for {service}.

**Guardrails Already Passed:**
- Not a high-risk action (delete, terminate, shutdown, etc.)
- Not a critical service (payment-service, auth-service, database-primary, kafka-broker)
- Confidence is above 70%

**Your Additional Checks:**
1. Does this action make sense for the diagnosed problem?
2. Are there any unintended side effects?
3. Is the action reversible?

Be conservative. If unsure, require human approval.""")
            
            prompt = f"""Assess this plan:
Action: {sanitized_action}
Severity: {severity}
Confidence: {confidence:.0%}

Provide:
1. **Safety Assessment**: Is this action safe to execute?
2. **Approval Gateway**: Does this require human approval? (Answer 'YES' if uncertain, 'NO' otherwise)"""
            
            messages = [system_prompt] + state.get("messages", []) + [HumanMessage(content=prompt)]
            response = llm.invoke(messages)
            tracker.track_tokens(str(messages), response.content)
            
            llm_reasoning = response.content
            
            # Determine approval requirement from LLM response
            llm_requires_approval = "YES" in llm_reasoning.upper()
            
            # Final decision: require approval if LLM says YES or severity is high
            requires_approval = llm_requires_approval or severity in ["critical", "high"]
            
        except Exception as e:
            llm_reasoning = f"Validation failed: {e}"
            requires_approval = True  # Fail-safe: require approval
            sanitized_action = action
            response = HumanMessage(content=llm_reasoning)
    
    return {
        "requires_approval": requires_approval,
        "messages": [response],
        "events": [create_event(
            "validate_action",
            f"Validation complete. Requires approval: {requires_approval}",
            llm_reasoning=llm_reasoning,
            guardrail_passed=True,
            sanitized_action=sanitized_action,
        )],
    }
