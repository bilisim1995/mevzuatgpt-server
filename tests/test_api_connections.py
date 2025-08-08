#!/usr/bin/env python3
"""
API Connection Tests for MevzuatGPT
Tests OpenAI and Groq API connections
"""

import asyncio
import os
import sys
import time
from typing import Dict, Any

# Add project root to path
sys.path.append('/home/runner/workspace')

from services.groq_service import GroqService
from services.embedding_service import EmbeddingService
from core.config import Settings

class APIConnectionTester:
    """Test API connections for OpenAI and Groq"""
    
    def __init__(self):
        self.settings = Settings()
        self.results = {}
    
    async def test_openai_embedding(self) -> Dict[str, Any]:
        """Test OpenAI embedding API connection"""
        print("🔍 Testing OpenAI Embedding API...")
        
        try:
            start_time = time.time()
            
            # Initialize embedding service
            embedding_service = EmbeddingService()
            
            # Test embedding with a simple text
            test_text = "Bu bir API bağlantı testidir."
            
            embedding = await embedding_service.generate_embedding(test_text)
            
            end_time = time.time()
            
            result = {
                "status": "SUCCESS",
                "response_time": round((end_time - start_time) * 1000, 2),  # ms
                "embedding_dimension": len(embedding) if embedding else 0,
                "api_key_valid": True,
                "model_used": self.settings.OPENAI_EMBEDDING_MODEL,
                "error": None
            }
            
            print(f"✅ OpenAI Embedding: SUCCESS ({result['response_time']}ms)")
            print(f"   Model: {result['model_used']}")
            print(f"   Dimension: {result['embedding_dimension']}")
            
            return result
            
        except Exception as e:
            result = {
                "status": "FAILED",
                "response_time": None,
                "embedding_dimension": 0,
                "api_key_valid": False,
                "model_used": self.settings.OPENAI_EMBEDDING_MODEL,
                "error": str(e)
            }
            
            print(f"❌ OpenAI Embedding: FAILED")
            print(f"   Error: {str(e)}")
            
            return result
    
    async def test_groq_inference(self) -> Dict[str, Any]:
        """Test Groq inference API connection"""
        print("🧠 Testing Groq AI Inference API...")
        
        try:
            start_time = time.time()
            
            # Initialize Groq service
            groq_service = GroqService()
            
            # Test AI inference with a simple prompt
            test_prompt = "Merhaba, bu bir API test mesajıdır."
            test_context = "Bu bir test bağlamıdır."
            
            response = await groq_service.generate_response(
                prompt=test_prompt,
                context=test_context,
                max_tokens=100,
                temperature=0.1
            )
            
            end_time = time.time()
            
            result = {
                "status": "SUCCESS",
                "response_time": round((end_time - start_time) * 1000, 2),  # ms
                "response_length": len(response.get("response", "")),
                "api_key_valid": True,
                "model_used": response.get("model_used", "unknown"),
                "token_usage": response.get("token_usage", {}),
                "confidence_score": response.get("confidence_score", 0.0),
                "error": None
            }
            
            print(f"✅ Groq Inference: SUCCESS ({result['response_time']}ms)")
            print(f"   Model: {result['model_used']}")
            print(f"   Response Length: {result['response_length']} chars")
            print(f"   Confidence: {result['confidence_score']:.2f}")
            
            return result
            
        except Exception as e:
            result = {
                "status": "FAILED",
                "response_time": None,
                "response_length": 0,
                "api_key_valid": False,
                "model_used": "llama3-8b-8192",
                "token_usage": {},
                "confidence_score": 0.0,
                "error": str(e)
            }
            
            print(f"❌ Groq Inference: FAILED")
            print(f"   Error: {str(e)}")
            
            return result
    
    async def test_combined_pipeline(self) -> Dict[str, Any]:
        """Test combined OpenAI + Groq pipeline"""
        print("🔄 Testing Combined AI Pipeline...")
        
        try:
            start_time = time.time()
            
            # Test full pipeline: embedding + inference
            test_query = "Türkiye'de şirket kurmak için gerekli belgeler nelerdir?"
            
            # Step 1: Generate embedding
            embedding_service = EmbeddingService()
            embedding = await embedding_service.generate_embedding(test_query)
            
            # Step 2: Simulate context from search results
            mock_context = """
            [KAYNAK 1]
            Belge: Şirket Kuruluş Rehberi
            Kurum: Ticaret Bakanlığı
            İçerik: Şirket kurmak için nüfus cüzdanı, adres belgesi ve vergi numarası gereklidir.
            """
            
            # Step 3: Generate AI response
            groq_service = GroqService()
            ai_response = await groq_service.generate_response(
                prompt=test_query,
                context=mock_context,
                max_tokens=200,
                temperature=0.1
            )
            
            end_time = time.time()
            
            result = {
                "status": "SUCCESS",
                "total_time": round((end_time - start_time) * 1000, 2),  # ms
                "embedding_success": len(embedding) > 0 if embedding else False,
                "ai_response_success": bool(ai_response.get("response")),
                "pipeline_functional": True,
                "error": None
            }
            
            print(f"✅ Combined Pipeline: SUCCESS ({result['total_time']}ms)")
            print(f"   Embedding: {'✅' if result['embedding_success'] else '❌'}")
            print(f"   AI Response: {'✅' if result['ai_response_success'] else '❌'}")
            
            return result
            
        except Exception as e:
            result = {
                "status": "FAILED",
                "total_time": None,
                "embedding_success": False,
                "ai_response_success": False,
                "pipeline_functional": False,
                "error": str(e)
            }
            
            print(f"❌ Combined Pipeline: FAILED")
            print(f"   Error: {str(e)}")
            
            return result
    
    async def run_all_tests(self):
        """Run all API connection tests"""
        print("🚀 MevzuatGPT API Connection Tests")
        print("=" * 50)
        
        # Test OpenAI
        openai_result = await self.test_openai_embedding()
        self.results["openai"] = openai_result
        
        print()
        
        # Test Groq
        groq_result = await self.test_groq_inference()
        self.results["groq"] = groq_result
        
        print()
        
        # Test Combined Pipeline
        pipeline_result = await self.test_combined_pipeline()
        self.results["pipeline"] = pipeline_result
        
        print()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("📊 TEST SUMMARY")
        print("=" * 30)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["status"] == "SUCCESS")
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests / total_tests * 100):.1f}%")
        
        print("\nDETAILS:")
        
        if self.results.get("openai", {}).get("status") == "SUCCESS":
            openai = self.results["openai"]
            print(f"✅ OpenAI: {openai['response_time']}ms, {openai['embedding_dimension']}D vectors")
        else:
            print("❌ OpenAI: Connection failed")
        
        if self.results.get("groq", {}).get("status") == "SUCCESS":
            groq = self.results["groq"]
            print(f"✅ Groq: {groq['response_time']}ms, {groq['model_used']}")
        else:
            print("❌ Groq: Connection failed")
        
        if self.results.get("pipeline", {}).get("status") == "SUCCESS":
            pipeline = self.results["pipeline"]
            print(f"✅ Pipeline: {pipeline['total_time']}ms end-to-end")
        else:
            print("❌ Pipeline: Integration failed")
        
        print("\n🎯 READY FOR PRODUCTION!" if passed_tests == total_tests else "\n⚠️  Fix failed connections before deployment")

async def main():
    """Main test runner"""
    tester = APIConnectionTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())