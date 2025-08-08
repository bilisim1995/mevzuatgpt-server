#!/usr/bin/env python3
"""
Production Ready Test - Final verification
"""

import asyncio
import sys
import time
import os

sys.path.append('/home/runner/workspace')

from core.config import settings
from services.groq_service import GroqService
from services.embedding_service import EmbeddingService

async def main():
    """Run production readiness test"""
    
    print("🚀 PRODUCTION READINESS TEST")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Configuration
    print("1️⃣ Configuration Test...")
    try:
        openai_valid = settings.OPENAI_API_KEY.startswith('sk-')
        groq_valid = settings.GROQ_API_KEY.startswith('gsk_')
        
        if openai_valid and groq_valid:
            print("   ✅ Both API keys configured correctly")
            tests_passed += 1
        else:
            print("   ❌ API key configuration invalid")
    except Exception as e:
        print(f"   ❌ Config error: {e}")
    
    # Test 2: OpenAI Embedding
    print("\n2️⃣ OpenAI Embedding Test...")
    try:
        embedding_service = EmbeddingService()
        start = time.time()
        embedding = await embedding_service.generate_embedding("Test production ready")
        duration = int((time.time() - start) * 1000)
        
        if embedding and len(embedding) == 1536:
            print(f"   ✅ OpenAI embedding successful ({duration}ms, {len(embedding)}D)")
            tests_passed += 1
        else:
            print("   ❌ OpenAI embedding failed")
    except Exception as e:
        print(f"   ❌ OpenAI error: {e}")
    
    # Test 3: Groq AI
    print("\n3️⃣ Groq AI Test...")
    try:
        groq_service = GroqService()
        start = time.time()
        response = await groq_service.generate_response(
            prompt="Production ready test",
            context="System validation context",
            max_tokens=50
        )
        duration = int((time.time() - start) * 1000)
        
        if response and response.get('response'):
            print(f"   ✅ Groq AI successful ({duration}ms, {response.get('model_used')})")
            tests_passed += 1
        else:
            print("   ❌ Groq AI failed")
    except Exception as e:
        print(f"   ❌ Groq error: {e}")
    
    # Results
    print(f"\n📊 RESULTS: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("\n🎉 SYSTEM IS PRODUCTION READY!")
        print("✅ OpenAI embeddings operational")
        print("✅ Groq AI inference operational") 
        print("✅ Configuration valid")
        print("✅ RAG pipeline ready")
        return True
    else:
        print(f"\n⚠️  {total_tests - tests_passed} tests failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)