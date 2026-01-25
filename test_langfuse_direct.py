#!/usr/bin/env python
"""
Direct Langfuse test - verify tracing works.
"""
import os
from app.config import settings

# Set environment variables BEFORE importing CallbackHandler
os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key  
os.environ["LANGFUSE_HOST"] = settings.langfuse_host

from langfuse.langchain import CallbackHandler
from langchain_google_genai import ChatGoogleGenerativeAI

print("=" * 60)
print("🧪 Testing Langfuse Direct Integration")
print("=" * 60)

# Check config
print(f"\n1. Configuration:")
print(f"   Langfuse Enabled: {settings.langfuse_enabled}")
print(f"   Public Key: {settings.langfuse_public_key[:20] if settings.langfuse_public_key else 'MISSING'}...")
print(f"   Secret Key: {settings.langfuse_secret_key[:20] if settings.langfuse_secret_key else 'MISSING'}...")
print(f"   Host: {settings.langfuse_host}")
print(f"   LLM Provider: {settings.llm_provider}")

if not settings.langfuse_enabled:
    print("\n❌ Langfuse not configured. Check .env file.")
    exit(1)

# Create handler
print(f"\n2. Creating Langfuse handler...")
try:
    handler = CallbackHandler()
    print("   ✅ Handler created successfully (no auth error)")
except Exception as e:
    print(f"   ❌ Failed to create handler: {e}")
    exit(1)

# Create LLM
print(f"\n3. Creating LLM ({settings.llm_provider})...")
llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    google_api_key=settings.google_api_key,
    temperature=0.3,
)

llm = llm.with_config({"callbacks": [handler]})
print("   ✅ LLM configured with Langfuse callback")

# Make test call
print(f"\n4. Making test LLM call...")
try:
    response = llm.invoke("Say 'Hello from NVIDIA Triage!' in exactly 5 words.")
    answer = response.content if hasattr(response, 'content') else str(response)
    print(f"   ✅ Response: {answer}")
except Exception as e:
    print(f"   ❌ LLM call failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print(f"\n" + "=" * 60)
print("✅ TEST COMPLETE!")
print("=" * 60)
print("\n📊 Check Langfuse Dashboard:")
print("   URL: https://us.cloud.langfuse.com")
print("   Look for a new trace (last 1 minute)")
print("\n   You should see:")
print("   - 1 trace")
print("   - 1 LLM generation (Gemini)")
print("   - Prompt + Response")
print("   - Token counts")
print("\n⏰ Traces appear within 10-30 seconds.")
print("=" * 60)
