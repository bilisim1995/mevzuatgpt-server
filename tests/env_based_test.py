#!/usr/bin/env python3
"""
Test system using .env file exclusively (no Replit Secrets)
"""

import asyncio
import sys
import time
from dotenv import load_dotenv
import os

sys.path.append('/home/runner/workspace')

# Force load .env
load_dotenv('.env', override=True)

from core.config import settings
from services.groq_service import GroqService
from services.embedding_service import EmbeddingService

async def test_env_only_system():
    """Test system using only .env file"""
    
    print("🔧 .ENV-ONLY SYSTEM TEST")
    print("=" * 40)
    
    # Show environment source
    print("📁 Environment Variables:")
    print(f"   OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY', 'Missing')[:30]}...")
    print(f"   GROQ_API_KEY: {os.getenv('GROQ_API_KEY', 'Missing')[:30]}...")
    print(f"   AI_PROVIDER: {os.getenv('AI_PROVIDER', 'Missing')}")
    
    print(f"\n⚙️  Settings Values:")
    print(f"   settings.OPENAI_API_KEY: {settings.OPENAI_API_KEY[:30]}...")
    print(f"   settings.GROQ_API_KEY: {settings.GROQ_API_KEY[:30]}...")
    print(f"   settings.AI_PROVIDER: {settings.AI_PROVIDER}")
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: OpenAI Embedding
    print(f"\n1️⃣ OpenAI Embedding (.env source)...")
    try:
        embedding_service = EmbeddingService()
        start = time.time()
        embedding = await embedding_service.generate_embedding("VPS deployment test")
        duration = int((time.time() - start) * 1000)
        
        if embedding and len(embedding) == 1536:
            print(f"   ✅ SUCCESS: {duration}ms, {len(embedding)}D vectors")
            tests_passed += 1
        else:
            print("   ❌ FAILED: No embedding generated")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    # Test 2: Groq AI
    print(f"\n2️⃣ Groq AI (.env source)...")
    try:
        groq_service = GroqService()
        start = time.time()
        response = await groq_service.generate_response(
            prompt="VPS deployment ready test",
            context="Testing .env configuration",
            max_tokens=50
        )
        duration = int((time.time() - start) * 1000)
        
        if response and response.get('response'):
            print(f"   ✅ SUCCESS: {duration}ms, {response.get('model_used', 'unknown')}")
            tests_passed += 1
        else:
            print("   ❌ FAILED: No response generated")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    # Test 3: Combined Pipeline
    print(f"\n3️⃣ Full Pipeline (.env source)...")
    try:
        start = time.time()
        
        # Embedding
        embedding = await embedding_service.generate_embedding("Test query for VPS")
        
        # AI Response  
        ai_response = await groq_service.generate_response(
            prompt="Test query for VPS",
            context="Mock context for pipeline test",
            max_tokens=50
        )
        
        duration = int((time.time() - start) * 1000)
        
        if embedding and ai_response.get('response'):
            print(f"   ✅ SUCCESS: {duration}ms total pipeline")
            tests_passed += 1
        else:
            print("   ❌ FAILED: Pipeline incomplete")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    # Results
    print(f"\n📊 RESULTS: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print(f"\n🎉 VPS-READY SYSTEM!")
        print("✅ No Replit Secrets dependency")
        print("✅ All configs from .env file")
        print("✅ OpenAI + Groq working")
        print("✅ Ready for VPS deployment")
        return True
    else:
        print(f"\n⚠️  {total_tests - tests_passed} tests failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_env_only_system())
    print(f"\nVPS deployment ready: {'YES' if success else 'NO'}")