#!/usr/bin/env python3
"""
Final API Test with New OpenAI Key
"""

import asyncio
import os
import sys
import time

sys.path.append('/home/runner/workspace')

from services.groq_service import GroqService
from services.embedding_service import EmbeddingService

async def test_with_new_key():
    """Test both APIs with the correct new key"""
    
    # Set the correct new OpenAI key
    os.environ['OPENAI_API_KEY'] = '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'
    
    print("🚀 FINAL API TEST WITH CORRECT KEYS")
    print("=" * 50)
    
    success_count = 0
    
    # Test OpenAI Embedding
    try:
        print("🔍 Testing OpenAI Embedding API...")
        start = time.time()
        
        embedding_service = EmbeddingService()
        embedding = await embedding_service.generate_embedding("Test embedding with new key")
        
        end = time.time()
        
        if embedding and len(embedding) > 0:
            print(f"✅ OpenAI: SUCCESS ({int((end-start)*1000)}ms, {len(embedding)}D)")
            success_count += 1
        else:
            print("❌ OpenAI: No embedding returned")
    except Exception as e:
        print(f"❌ OpenAI: {str(e)}")
    
    print()
    
    # Test Groq Inference  
    try:
        print("🧠 Testing Groq AI Inference API...")
        start = time.time()
        
        groq_service = GroqService()
        response = await groq_service.generate_response(
            prompt="Bu bir final testtir",
            context="Test context for final verification",
            max_tokens=100
        )
        
        end = time.time()
        
        if response and response.get("response"):
            print(f"✅ Groq: SUCCESS ({int((end-start)*1000)}ms, {response.get('model_used', 'unknown')})")
            success_count += 1
        else:
            print("❌ Groq: No response returned")
    except Exception as e:
        print(f"❌ Groq: {str(e)}")
    
    print()
    
    # Test Combined Pipeline
    try:
        print("🔄 Testing Full Pipeline...")
        start = time.time()
        
        # Step 1: Embedding
        embedding = await embedding_service.generate_embedding("Pipeline test query")
        
        # Step 2: AI Response
        ai_response = await groq_service.generate_response(
            prompt="Pipeline test query",
            context="Mock search results for pipeline test",
            max_tokens=150
        )
        
        end = time.time()
        
        if embedding and ai_response.get("response"):
            print(f"✅ Pipeline: SUCCESS ({int((end-start)*1000)}ms total)")
            success_count += 1
        else:
            print("❌ Pipeline: Failed")
    except Exception as e:
        print(f"❌ Pipeline: {str(e)}")
    
    print()
    print("📊 FINAL RESULTS")
    print("=" * 30)
    print(f"Tests Passed: {success_count}/3")
    
    if success_count == 3:
        print("🎉 ALL SYSTEMS OPERATIONAL!")
        print("✅ OpenAI Embeddings: Ready")  
        print("✅ Groq AI Generation: Ready")
        print("✅ Full RAG Pipeline: Ready")
        print("\n🚀 SYSTEM READY FOR PRODUCTION!")
    else:
        print("⚠️  Some tests failed - check API keys")

if __name__ == "__main__":
    asyncio.run(test_with_new_key())