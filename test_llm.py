#!/usr/bin/env python
"""
Quick test to verify OpenRouter and Langfuse integration.
"""
import asyncio
from app.agents.llm import get_llm

async def test_llm_and_tracing():
    print("=" * 60)
    print("Testing LLM Configuration & Langfuse Tracing")
    print("=" * 60)
    
    # Test LLM call
    print("\n1. Getting LLM instance...")
    llm = get_llm(trace_name="test_llm_openrouter")
    print(f"   ✓ LLM configured: {llm.__class__.__name__}")
    
    print("\n2. Sending test prompt...")
    prompt = "What is 2+2? Answer in one sentence."
    
    try:
        response = llm.invoke(prompt)
        answer = response.content if hasattr(response, 'content') else str(response)
        print(f"   ✓ Response: {answer}")
        
        print("\n3. Langfuse Trace:")
        print("   → Go to: https://us.cloud.langfuse.com")
        print("   → Look for trace: 'test_llm_openrouter'")
        print("   → You should see:")
        print("      - Prompt: 'What is 2+2?'")
        print(f"      - Response: '{answer}'")
        print("      - Latency, tokens, cost")
        
        print("\n✅ SUCCESS! LLM and Langfuse are working!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting:")
        print("- Check OPENROUTER_API_KEY in .env")
        print("- Check LLM_PROVIDER=openrouter in config.py")
        print("- Restart uvicorn if it's running")

if __name__ == "__main__":
    asyncio.run(test_llm_and_tracing())
