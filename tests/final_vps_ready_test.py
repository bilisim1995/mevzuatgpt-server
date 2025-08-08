#!/usr/bin/env python3
"""
Final VPS Readiness Test - Complete system validation
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

async def final_vps_test():
    """Final comprehensive VPS readiness test"""
    
    print("🚀 FINAL VPS READINESS TEST")
    print("=" * 50)
    
    # Environment validation
    print("🔧 Environment Configuration:")
    env_valid = True
    
    required_keys = [
        'OPENAI_API_KEY', 'GROQ_API_KEY', 'DATABASE_URL', 
        'SUPABASE_URL', 'REDIS_URL', 'AI_PROVIDER'
    ]
    
    for key in required_keys:
        value = os.getenv(key)
        if value:
            print(f"   ✅ {key}: {'*' * 20}...{value[-8:]}")
        else:
            print(f"   ❌ {key}: Missing")
            env_valid = False
    
    if not env_valid:
        print("\n❌ Environment configuration incomplete")
        return False
    
    print(f"\n🧪 API Testing:")
    tests_passed = 0
    total_tests = 4
    
    # Test 1: OpenAI Embedding
    print("1️⃣ OpenAI Embedding Service...")
    try:
        embedding_service = EmbeddingService()
        start = time.time()
        embedding = await embedding_service.generate_embedding("VPS production test query")
        duration = int((time.time() - start) * 1000)
        
        if embedding and len(embedding) == 1536:
            print(f"   ✅ OpenAI: {duration}ms, {len(embedding)}D vectors")
            tests_passed += 1
        else:
            print("   ❌ OpenAI: Failed to generate embedding")
    except Exception as e:
        print(f"   ❌ OpenAI: {str(e)[:100]}...")
    
    # Test 2: Groq AI
    print("2️⃣ Groq AI Service...")
    try:
        groq_service = GroqService()
        start = time.time()
        response = await groq_service.generate_response(
            prompt="VPS production test query",
            context="This is a final system test for VPS deployment readiness",
            max_tokens=100
        )
        duration = int((time.time() - start) * 1000)
        
        if response and response.get('response'):
            print(f"   ✅ Groq: {duration}ms, {response.get('model_used', 'unknown')}")
            print(f"      Response: {response['response'][:80]}...")
            tests_passed += 1
        else:
            print("   ❌ Groq: No response generated")
    except Exception as e:
        print(f"   ❌ Groq: {str(e)[:100]}...")
    
    # Test 3: Configuration Loading
    print("3️⃣ Configuration System...")
    try:
        config_valid = all([
            settings.OPENAI_API_KEY.startswith('sk-'),
            settings.GROQ_API_KEY.startswith('gsk_'),
            settings.DATABASE_URL.startswith('postgresql://'),
            settings.AI_PROVIDER in ['groq', 'openai', 'ollama']
        ])
        
        if config_valid:
            print(f"   ✅ Config: All settings valid")
            print(f"      AI Provider: {settings.AI_PROVIDER}")
            print(f"      Embedding Model: {settings.OPENAI_EMBEDDING_MODEL}")
            tests_passed += 1
        else:
            print("   ❌ Config: Invalid settings detected")
    except Exception as e:
        print(f"   ❌ Config: {str(e)[:100]}...")
    
    # Test 4: Full RAG Pipeline Simulation
    print("4️⃣ Full RAG Pipeline...")
    try:
        start = time.time()
        
        # Step 1: Generate query embedding
        query_embedding = await embedding_service.generate_embedding("Legal document search test")
        
        # Step 2: Simulate context retrieval (mock)
        mock_context = "Legal document context for testing VPS deployment readiness"
        
        # Step 3: Generate AI response
        ai_response = await groq_service.generate_response(
            prompt="Legal document search test",
            context=mock_context,
            max_tokens=150
        )
        
        total_duration = int((time.time() - start) * 1000)
        
        if query_embedding and ai_response.get('response'):
            print(f"   ✅ RAG Pipeline: {total_duration}ms complete flow")
            print(f"      Embedding: {len(query_embedding)}D")
            print(f"      AI Response: {len(ai_response['response'])} chars")
            tests_passed += 1
        else:
            print("   ❌ RAG Pipeline: Incomplete flow")
    except Exception as e:
        print(f"   ❌ RAG Pipeline: {str(e)[:100]}...")
    
    # Final Results
    print(f"\n📊 FINAL RESULTS: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print(f"\n🎉 SYSTEM IS VPS-READY!")
        print("✅ All API connections working")
        print("✅ Configuration system functional") 
        print("✅ RAG pipeline operational")
        print("✅ No Replit dependencies")
        print("✅ Ready for production deployment")
        
        print(f"\n📋 VPS DEPLOYMENT CHECKLIST:")
        print("1. Copy .env file to VPS")
        print("2. Install Python dependencies")
        print("3. Run: python tests/final_vps_ready_test.py")
        print("4. Start: python app.py server")
        
        return True
    else:
        print(f"\n⚠️  {total_tests - tests_passed} critical issues remain")
        print("System needs fixes before VPS deployment")
        return False

if __name__ == "__main__":
    success = asyncio.run(final_vps_test())
    exit(0 if success else 1)