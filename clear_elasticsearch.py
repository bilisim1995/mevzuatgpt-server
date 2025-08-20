#!/usr/bin/env python3
"""
Elasticsearch'teki tüm embedding'leri temizle
"""
import asyncio
import sys
import os
sys.path.append('.')

from services.elasticsearch_service import ElasticsearchService
from services.embedding_service import EmbeddingService

async def clear_all_embeddings():
    """Tüm embedding'leri temizle"""
    print("🗑️ Elasticsearch embedding temizlik başlıyor...")
    
    try:
        # Elasticsearch service başlat
        es_service = ElasticsearchService()
        
        # Index var mı kontrol et
        index_exists = await es_service.client.indices.exists(index="mevzuat_embeddings")
        print(f"📋 Index durumu: {'Var' if index_exists else 'Yok'}")
        
        if index_exists:
            # Temizlik öncesi count
            count_before = await es_service.client.count(index="mevzuat_embeddings")
            total_before = count_before['count']
            print(f"📊 Temizlik öncesi embedding sayısı: {total_before}")
            
            # Tüm dökümanları sil
            result = await es_service.client.delete_by_query(
                index="mevzuat_embeddings",
                body={
                    "query": {
                        "match_all": {}
                    }
                },
                refresh=True
            )
            
            deleted_count = result.get('deleted', 0)
            print(f"✅ Silinen embedding sayısı: {deleted_count}")
            
            # Temizlik sonrası count
            count_after = await es_service.client.count(index="mevzuat_embeddings")
            total_after = count_after['count']
            print(f"📊 Temizlik sonrası embedding sayısı: {total_after}")
            
        else:
            print("ℹ️ Index bulunamadı - zaten temiz")
        
        await es_service.close()
        print("✅ Elasticsearch temizlik tamamlandı")
        
    except Exception as e:
        print(f"❌ Temizlik hatası: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(clear_all_embeddings())