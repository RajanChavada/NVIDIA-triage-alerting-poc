"""
Enhanced LLM wrapper with automatic metrics tracking and debug logging.
"""
import os
import time
from datetime import datetime
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from app.config import settings
from app.agents.observability import add_node_metrics, NodeMetrics, estimate_cost


def get_llm(trace_name: str = None) -> BaseChatModel:
    """Get configured LLM with Langfuse tracing."""
    
    if settings.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")
        
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0.3,
            convert_system_message_to_human=True,
        )
    
    elif settings.llm_provider == "openrouter":
        from langchain_openai import ChatOpenAI

        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter")
        
        llm = ChatOpenAI(
            model=settings.openrouter_model,
            openai_api_key=settings.openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://nvidia-triage-alerting.com",
                "X-Title": "NVIDIA Triage Alerting MVP",
            },
            temperature=0.3,
        )
    
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
    
    # Add Langfuse callback if enabled
    if settings.langfuse_enabled:
        try:
            os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
            os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
            os.environ["LANGFUSE_HOST"] = settings.langfuse_host
            
            from langfuse.langchain import CallbackHandler
            handler = CallbackHandler()
            llm = llm.with_config({"callbacks": [handler]})
        except Exception as e:
            print(f"⚠️ Langfuse disabled: {e}")
    
    return llm


class MetricsTracker:
    """Context manager to track metrics for a node execution."""
    
    def __init__(self, triage_id: str, node_name: str, llm_model: str = None):
        self.triage_id = triage_id
        self.node_name = node_name
        self.llm_model = llm_model or (settings.gemini_model if settings.llm_provider == "gemini" else settings.openrouter_model)
        self.start_time = None
        self.prompt_tokens = 0
        self.completion_tokens = 0
        print(f"📊 [METRICS] Tracker initialized: node={node_name}, triage={triage_id}")
        
    def __enter__(self):
        self.start_time = datetime.now()
        print(f"📊 [METRICS] Entering {self.node_name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.now()
        duration_ms = (end_time - self.start_time).total_seconds() * 1000
        
        total_tokens = self.prompt_tokens + self.completion_tokens
        cost = estimate_cost(self.llm_model, self.prompt_tokens, self.completion_tokens)
        
        print(f"📊 [METRICS] Exiting {self.node_name}:")
        print(f"   - Duration: {duration_ms:.1f}ms")
        print(f"   - Tokens: {total_tokens} ({self.prompt_tokens} prompt + {self.completion_tokens} completion)")
        print(f"   - Cost: ${cost:.6f}")
        print(f"   - Success: {exc_type is None}")
        
        metrics = NodeMetrics(
            node_name=self.node_name,
            start_time=self.start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            llm_model=self.llm_model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            success=exc_type is None,
            error=str(exc_val) if exc_val else None,
        )
        
        try:
            add_node_metrics(self.triage_id, metrics)
            print(f"   ✅ Metrics saved successfully")
        except Exception as e:
            print(f"   ❌ Failed to save metrics: {e}")
        
        return False
    
    def track_tokens(self, prompt: str, response: str):
        """Estimate token counts (rough approximation: ~4 chars per token)."""
        self.prompt_tokens = len(prompt) // 4
        self.completion_tokens = len(response) // 4
        print(f"📊 [METRICS] Tokens tracked for {self.node_name}: {self.prompt_tokens} + {self.completion_tokens} = {self.prompt_tokens + self.completion_tokens}")
