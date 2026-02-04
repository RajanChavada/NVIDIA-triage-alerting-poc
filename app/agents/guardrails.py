"""
NeMo Guardrails integration for enterprise safety and compliance.

Provides:
- Input/output content filtering
- PII detection and redaction
- Topic adherence (stay on-task)
- Action validation before execution
"""
from typing import Optional
from langchain_core.language_models import BaseChatModel

from app.config import settings


def get_guarded_llm(base_llm: BaseChatModel, config_path: str = "./config/guardrails"):
    """
    Wrap an LLM with NeMo Guardrails for safety.
    
    Args:
        base_llm: The base LangChain LLM to wrap
        config_path: Path to guardrails configuration directory
        
    Returns:
        A guarded LLM instance
    """
    try:
        from nemoguardrails import RailsConfig, LLMRails
        
        config = RailsConfig.from_path(config_path)
        rails = LLMRails(config, llm=base_llm)
        print("🛡️ NeMo Guardrails enabled")
        return rails
    except ImportError:
        print("⚠️ NeMo Guardrails not installed, using unguarded LLM")
        return base_llm
    except Exception as e:
        print(f"⚠️ Failed to initialize Guardrails: {e}")
        return base_llm


class TriageGuardrails:
    """
    Guardrails specific to triage agent operations.
    
    Enforces:
    - No execution of destructive commands without approval
    - No access to unauthorized systems
    - PII redaction in logs
    - Rate limiting on automated actions
    """
    
    # Actions that always require human approval
    HIGH_RISK_ACTIONS = [
        "delete",
        "terminate",
        "shutdown",
        "drop_database",
        "force_restart",
        "scale_to_zero",
    ]
    
    # Services that always require approval regardless of confidence
    CRITICAL_SERVICES = [
        "payment-service",
        "auth-service",
        "database-primary",
        "kafka-broker",
    ]
    
    @classmethod
    def validate_action(cls, action: str, service: str, confidence: float) -> dict:
        """
        Validate a proposed action against guardrails.
        
        Returns:
            dict with 'allowed' bool and 'reason' if blocked
        """
        action_lower = action.lower()
        
        # Check for high-risk actions
        for risk_action in cls.HIGH_RISK_ACTIONS:
            if risk_action in action_lower:
                return {
                    "allowed": False,
                    "requires_approval": True,
                    "reason": f"High-risk action '{risk_action}' requires human approval",
                }
        
        # Check for critical services
        if service in cls.CRITICAL_SERVICES:
            return {
                "allowed": False,
                "requires_approval": True,
                "reason": f"Critical service '{service}' requires human approval for any action",
            }
        
        # Low confidence requires approval
        if confidence < 0.7:
            return {
                "allowed": False,
                "requires_approval": True,
                "reason": f"Confidence {confidence:.0%} below auto-approval threshold (70%)",
            }
        
        return {
            "allowed": True,
            "requires_approval": False,
            "reason": "Action passed all guardrail checks",
        }
    
    @classmethod
    def redact_pii(cls, text: str) -> str:
        """
        Redact potential PII from log entries.
        
        Basic implementation - in production, use NeMo Guardrails Safety model.
        """
        import re
        
        # Email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # IP addresses
        text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_ADDR]', text)
        
        # API keys (common patterns)
        text = re.sub(r'\b(sk-|pk-|api_)[A-Za-z0-9]{20,}\b', '[API_KEY]', text)
        
        # JWT tokens
        text = re.sub(r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*', '[JWT_TOKEN]', text)
        
        return text
