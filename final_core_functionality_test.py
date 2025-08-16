#!/usr/bin/env python3
"""
CORE FUNCTIONALITY TEST - Authentication Olmadan
Direct service calls ile tam sistem testini yapacağız
"""
import asyncio
import json
from io import BytesIO
import os

async def test_core_functionality():
    """Core functionality comprehensive test"""
    
    print("🎯 CORE FUNCTIONALITY TEST")
    print("=" * 28)
    print("Authentication bypassed - Direct service testing")
    
    try:
        # Test 1: Elasticsearch Health & Storage
        await test_elasticsearch_comprehensive()
        
        # Test 2: Document Processing Simulation  
        await test_document_processing_pipeline()
        
        # Test 3: Advanced Search Tests
        await test_advanced_search_scenarios()
        
        # Test 4: AI Integration Test
        await test_ai_integration_direct()
        
        # Test 5: Performance Benchmarks
        await test_performance_benchmarks()
        
        print("\n🏆 CORE FUNCTIONALITY TEST COMPLETED!")
        print("=" * 37)
        
    except Exception as e:
        print(f"❌ Core test error: {e}")
        import traceback
        traceback.print_exc()

async def test_elasticsearch_comprehensive():
    """Comprehensive Elasticsearch testing"""
    print("\n1️⃣ ELASTICSEARCH COMPREHENSIVE TEST")
    
    try:
        from services.elasticsearch_service import ElasticsearchService
        from services.embedding_service import EmbeddingService
        
        # Elasticsearch health
        es_service = ElasticsearchService()
        health = await es_service.health_check()
        
        print(f"✅ Cluster Status: {health['cluster_status']}")
        print(f"✅ Document Count: {health['document_count']}")
        print(f"✅ Vector Dimensions: {health['vector_dimensions']}")
        
        # Index details
        try:
            index_info = await es_service.get_index_info()
            print(f"✅ Index Settings: {index_info}")
        except:
            print("⚠️ Index info not available")
        
        # Embedding service test
        embedding_service = EmbeddingService()
        total_embeddings = await embedding_service.get_embeddings_count()
        print(f"✅ Total Embeddings: {total_embeddings}")
        
        # Test embedding generation
        test_text = "Sosyal güvenlik mevzuatı test metni"
        embedding = await embedding_service.generate_embedding(test_text)
        print(f"✅ Embedding Generation: {len(embedding)}D vector")
        
    except Exception as e:
        print(f"❌ Elasticsearch test error: {e}")

async def test_document_processing_pipeline():
    """Document processing pipeline simulation"""
    print("\n2️⃣ DOCUMENT PROCESSING PIPELINE TEST")
    
    try:
        from tasks.document_processor import DocumentProcessor
        from services.embedding_service import EmbeddingService
        
        # Create test document content
        test_content = """
        SOSYAL GÜVENLİK KANUNU TEST DOKÜMANI
        
        Madde 1: Sigortalılık Şartları
        Bu kanun kapsamında sigortalı sayılanlar:
        a) 18 yaşını doldurmuş Türkiye Cumhuriyeti vatandaşları
        b) Aylık geliri asgari ücretin yarısını geçenler
        c) Çalışma izni olan yabancı uyruklu kişiler
        
        Madde 2: Prim Ödeme Yükümlülüğü
        Sigortalının ve işverenin prim ödeme yükümlülüğü vardır.
        Primler her ayın 23'üne kadar SGK'ya yatırılır.
        Geciken primler için yasal faiz uygulanır.
        
        Madde 3: Emeklilik Şartları
        Erkekler: 65 yaş ve 7200 gün prim
        Kadınlar: 63 yaş ve 6300 gün prim
        Erken emeklilik: 25 yıl sigortalılık süresi
        
        Madde 4: İş Kazası Tazminatları
        Geçici iş göremezlik ödeneği günlük kazancın %66.6'sı
        Sürekli iş göremezlik durumunda aylık bağlanır
        Ölüm halinde dul ve yetim aylıkları verilir
        """
        
        # Text chunking simulation
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            length_function=len,
        )
        
        chunks = text_splitter.split_text(test_content)
        print(f"✅ Text Chunking: {len(chunks)} chunks created")
        
        # Embedding generation for each chunk
        embedding_service = EmbeddingService()
        
        test_document_id = "test-comprehensive-doc"
        chunks_data = []
        
        for i, chunk in enumerate(chunks):
            if chunk.strip():  # Skip empty chunks
                embedding = await embedding_service.generate_embedding(chunk)
                
                chunk_data = {
                    "content": chunk.strip(),
                    "embedding": embedding,
                    "chunk_index": i,
                    "page_number": 1,
                    "line_start": i * 10,
                    "line_end": (i + 1) * 10,
                    "source_institution": "SGK",
                    "source_document": "sosyal_guvenlik_kanunu_test.pdf",
                    "metadata": {
                        "test_document": True,
                        "comprehensive_test": True
                    }
                }
                chunks_data.append(chunk_data)
        
        # Store embeddings
        embedding_ids = await embedding_service.store_embeddings(
            document_id=test_document_id,
            chunks=chunks_data
        )
        
        print(f"✅ Embeddings Stored: {len(embedding_ids)} vectors")
        print(f"✅ Document ID: {test_document_id}")
        
        # Verify storage
        doc_count = await embedding_service.get_embeddings_count(test_document_id)
        print(f"✅ Stored Verification: {doc_count} embeddings for document")
        
        return test_document_id
        
    except Exception as e:
        print(f"❌ Document processing error: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_advanced_search_scenarios():
    """Advanced search scenarios testing"""
    print("\n3️⃣ ADVANCED SEARCH SCENARIOS")
    
    try:
        from services.embedding_service import EmbeddingService
        
        embedding_service = EmbeddingService()
        
        # Complex search scenarios
        search_scenarios = [
            {
                "query": "sigortalılık şartları yaş sınırları",
                "expected_topics": ["sigortalılık", "yaş"],
                "description": "Age limit eligibility search"
            },
            {
                "query": "prim ödeme yükümlülüğü gecikme cezası",
                "expected_topics": ["prim", "gecikme", "faiz"],
                "description": "Premium payment delay penalties"
            },
            {
                "query": "emeklilik koşulları erkek kadın farkı",
                "expected_topics": ["emeklilik", "erkek", "kadın"],
                "description": "Retirement conditions gender differences"
            },
            {
                "query": "iş kazası tazminat miktarı hesaplama",
                "expected_topics": ["iş kazası", "tazminat", "hesaplama"],
                "description": "Work accident compensation calculation"
            },
            {
                "query": "sosyal güvenlik kapsamı yabancı işçi",
                "expected_topics": ["yabancı", "çalışma izni"],
                "description": "Foreign worker social security coverage"
            }
        ]
        
        for scenario in search_scenarios:
            print(f"\n🔍 Test: {scenario['description']}")
            print(f"   Query: '{scenario['query']}'")
            
            results = await embedding_service.similarity_search(
                query_text=scenario['query'],
                k=3,
                similarity_threshold=0.1
            )
            
            print(f"✅ Results: {len(results)} matches found")
            
            if results:
                best_match = results[0]
                print(f"   Best Match Similarity: {best_match['similarity']:.3f}")
                print(f"   Content Preview: {best_match['content'][:80]}...")
                
                # Check if expected topics are in results
                content_lower = best_match['content'].lower()
                found_topics = [topic for topic in scenario['expected_topics'] 
                              if topic.lower() in content_lower]
                
                if found_topics:
                    print(f"   ✅ Found Expected Topics: {found_topics}")
                else:
                    print(f"   ⚠️ Expected topics not found in top result")
        
    except Exception as e:
        print(f"❌ Advanced search error: {e}")

async def test_ai_integration_direct():
    """Direct AI integration testing"""
    print("\n4️⃣ AI INTEGRATION TEST (Direct)")
    
    try:
        from services.groq_service import GroqService
        from services.embedding_service import EmbeddingService
        
        # Get some sample search results
        embedding_service = EmbeddingService()
        
        search_results = await embedding_service.similarity_search(
            query_text="sigortalılık şartları nelerdir",
            k=3,
            similarity_threshold=0.2
        )
        
        if search_results:
            print(f"✅ Search Context: {len(search_results)} relevant documents")
            
            # Test AI response generation
            groq_service = GroqService()
            
            # Build context from search results
            context_parts = []
            for result in search_results:
                context_parts.append(f"Kaynak: {result['source_document']}")
                context_parts.append(f"İçerik: {result['content']}")
                context_parts.append("---")
            
            context = "\n".join(context_parts)
            
            query = "Sosyal güvenlik kapsamında sigortalılık şartları nelerdir?"
            
            # Generate AI response
            ai_response = await groq_service.generate_response(
                query=query,
                context=context,
                max_tokens=500
            )
            
            print(f"✅ AI Response Generated: {len(ai_response)} characters")
            print(f"📄 Response Preview: {ai_response[:150]}...")
            
            # Test response quality
            if any(keyword in ai_response.lower() for keyword in ['sigorta', 'yaş', 'şart']):
                print("✅ Response Quality: Contains relevant keywords")
            else:
                print("⚠️ Response Quality: May lack specific keywords")
                
        else:
            print("⚠️ No search results to test AI integration")
            
    except Exception as e:
        print(f"❌ AI integration error: {e}")

async def test_performance_benchmarks():
    """Performance benchmarks"""
    print("\n5️⃣ PERFORMANCE BENCHMARKS")
    
    try:
        from services.embedding_service import EmbeddingService
        import time
        
        embedding_service = EmbeddingService()
        
        # Embedding generation speed
        test_text = "Bu bir performans testi metnidir"
        
        start_time = time.time()
        embedding = await embedding_service.generate_embedding(test_text)
        embedding_time = time.time() - start_time
        
        print(f"✅ Embedding Generation: {embedding_time:.3f}s for 2048D vector")
        
        # Search speed test
        search_queries = [
            "sigortalılık şartları",
            "prim ödeme",
            "emeklilik yaşı",
            "iş kazası",
            "sosyal güvenlik"
        ]
        
        search_times = []
        for query in search_queries:
            start_time = time.time()
            results = await embedding_service.similarity_search(
                query_text=query,
                k=5,
                similarity_threshold=0.1
            )
            search_time = time.time() - start_time
            search_times.append(search_time)
            
        avg_search_time = sum(search_times) / len(search_times)
        
        print(f"✅ Average Search Time: {avg_search_time:.3f}s per query")
        print(f"✅ Fastest Search: {min(search_times):.3f}s")
        print(f"✅ Slowest Search: {max(search_times):.3f}s")
        
        # Memory efficiency check
        total_embeddings = await embedding_service.get_embeddings_count()
        estimated_memory = total_embeddings * 2048 * 4 / (1024*1024)  # MB
        
        print(f"✅ Memory Efficiency: ~{estimated_memory:.1f}MB for {total_embeddings} vectors")
        
    except Exception as e:
        print(f"❌ Performance test error: {e}")

if __name__ == "__main__":
    asyncio.run(test_core_functionality())