#!/usr/bin/env python3
"""
Elasticsearch Embedding Temizleme Script
=========================================

Bu script Elasticsearch'taki TÜM mevzuat embeddinglerini temizler.
Dikkat: Bu işlem geri alınamaz!

Kullanım:
    python tests/clear_all_embeddings.py

Özellikler:
- Elasticsearch bağlantı kontrolü
- Index varlık kontrolü
- Embedding sayısı raporu
- Güvenli silme işlemi
- Detaylı progress gösterimi
"""

import asyncio
import sys
import os
from datetime import datetime

# Proje kök dizinini Python path'ine ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.elasticsearch_service import ElasticsearchService
from core.config import get_settings


class EmbeddingCleaner:
    """Elasticsearch embedding temizleme sınıfı"""
    
    def __init__(self):
        self.settings = get_settings()
        self.es_service = ElasticsearchService()
        self.index_name = "mevzuat_embeddings"
    
    async def check_connection(self):
        """Elasticsearch bağlantısını kontrol et"""
        print("🔍 Elasticsearch bağlantısı kontrol ediliyor...")
        
        try:
            # Test connection with a simple ping
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.settings.ELASTICSEARCH_URL}/_cluster/health") as response:
                    if response.status == 200:
                        health = await response.json()
                        print(f"✅ Elasticsearch bağlantısı başarılı")
                        print(f"   • Cluster: {health.get('cluster_name', 'unknown')}")
                        print(f"   • Status: {health.get('status', 'unknown')}")
                        return True
                    else:
                        print(f"❌ Elasticsearch bağlantı hatası: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Elasticsearch bağlantı hatası: {str(e)}")
            return False
    
    async def check_index_exists(self):
        """Index varlığını kontrol et"""
        print(f"\n🔍 Index '{self.index_name}' varlığı kontrol ediliyor...")
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.head(f"{self.settings.ELASTICSEARCH_URL}/{self.index_name}") as response:
                    if response.status == 200:
                        print(f"✅ Index '{self.index_name}' mevcut")
                        return True
                    elif response.status == 404:
                        print(f"⚠️  Index '{self.index_name}' bulunamadı")
                        return False
                    else:
                        print(f"❌ Index kontrol hatası: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Index kontrol hatası: {str(e)}")
            return False
    
    async def get_embedding_count(self):
        """Mevcut embedding sayısını al"""
        print(f"\n📊 Embedding sayısı hesaplanıyor...")
        
        try:
            import aiohttp
            import json
            
            # Count all documents in the index
            query = {
                "query": {
                    "match_all": {}
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.settings.ELASTICSEARCH_URL}/{self.index_name}/_count",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(query)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        count = result.get('count', 0)
                        print(f"📊 Toplam embedding sayısı: {count:,}")
                        return count
                    else:
                        print(f"❌ Embedding sayısı alınamadı: {response.status}")
                        return 0
        except Exception as e:
            print(f"❌ Embedding sayısı alma hatası: {str(e)}")
            return 0
    
    async def get_documents_by_institution(self):
        """Kuruma göre doküman dağılımını göster"""
        print(f"\n📊 Kurum bazında embedding dağılımı:")
        
        try:
            import aiohttp
            import json
            
            # Aggregation query to group by document_id
            query = {
                "size": 0,
                "aggs": {
                    "documents": {
                        "terms": {
                            "field": "document_id.keyword",
                            "size": 1000
                        }
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.settings.ELASTICSEARCH_URL}/{self.index_name}/_search",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(query)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        buckets = result.get('aggregations', {}).get('documents', {}).get('buckets', [])
                        
                        if buckets:
                            print(f"   • Benzersiz doküman sayısı: {len(buckets)}")
                            for i, bucket in enumerate(buckets[:5]):  # İlk 5 dokümanı göster
                                doc_id = bucket['key'][:8] + '...'
                                count = bucket['doc_count']
                                print(f"   • {doc_id}: {count:,} embedding")
                            
                            if len(buckets) > 5:
                                print(f"   • ... ve {len(buckets) - 5} doküman daha")
                        else:
                            print("   • Hiç doküman bulunamadı")
                            
                    else:
                        print(f"❌ Doküman dağılımı alınamadı: {response.status}")
        except Exception as e:
            print(f"❌ Doküman dağılımı alma hatası: {str(e)}")
    
    async def clear_all_embeddings(self):
        """Tüm embedingleri temizle"""
        print(f"\n🗑️  TÜM EMBEDDİNGLER TEMİZLENİYOR...")
        print("=" * 50)
        
        try:
            import aiohttp
            import json
            
            # Delete by query - all documents
            delete_query = {
                "query": {
                    "match_all": {}
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.settings.ELASTICSEARCH_URL}/{self.index_name}/_delete_by_query?refresh=true",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(delete_query)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        deleted_count = result.get('deleted', 0)
                        took_ms = result.get('took', 0)
                        
                        print(f"✅ Silme işlemi tamamlandı!")
                        print(f"   • Silinen embedding sayısı: {deleted_count:,}")
                        print(f"   • İşlem süresi: {took_ms} ms")
                        
                        # Check for failures
                        failures = result.get('failures', [])
                        if failures:
                            print(f"⚠️  {len(failures)} adet hata oluştu")
                            for failure in failures[:3]:  # İlk 3 hatayı göster
                                print(f"     - {failure.get('cause', {}).get('reason', 'Bilinmeyen hata')}")
                        
                        return deleted_count
                    else:
                        error_text = await response.text()
                        print(f"❌ Silme işlemi başarısız: {response.status}")
                        print(f"   Hata: {error_text[:200]}")
                        return 0
                        
        except Exception as e:
            print(f"❌ Silme işlemi hatası: {str(e)}")
            return 0
    
    async def verify_cleanup(self):
        """Temizleme işlemini doğrula"""
        print(f"\n🔍 Temizleme doğrulaması...")
        
        final_count = await self.get_embedding_count()
        
        if final_count == 0:
            print("✅ Tüm embeddinglar başarıyla temizlendi!")
        else:
            print(f"⚠️  Hâlâ {final_count:,} embedding kaldı")
        
        return final_count
    
    async def run_cleanup(self):
        """Ana temizleme işlemini çalıştır"""
        start_time = datetime.now()
        
        print("🧹 ELASTICSEARCH EMBEDDİNG TEMİZLEME")
        print("=" * 50)
        print(f"Başlangıç zamanı: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Elasticsearch URL: {self.settings.ELASTICSEARCH_URL}")
        print(f"Target Index: {self.index_name}")
        print()
        
        # Step 1: Check connection
        if not await self.check_connection():
            print("\n❌ Elasticsearch bağlantısı kurulamadı!")
            return False
        
        # Step 2: Check if index exists
        if not await self.check_index_exists():
            print(f"\n✅ Index '{self.index_name}' zaten mevcut değil - temizlik gerekli değil!")
            return True
        
        # Step 3: Get current count
        initial_count = await self.get_embedding_count()
        if initial_count == 0:
            print("\n✅ Zaten hiç embedding yok - temizlik gerekli değil!")
            return True
        
        # Step 4: Show distribution
        await self.get_documents_by_institution()
        
        # Step 5: Confirm deletion
        print(f"\n⚠️  DİKKAT: {initial_count:,} adet embedding silinecek!")
        print("Bu işlem geri alınamaz!")
        
        response = input("\nDevam etmek için 'EVET' yazın (büyük harflerle): ")
        if response != 'EVET':
            print("❌ İşlem iptal edildi.")
            return False
        
        # Step 6: Delete all embeddings
        deleted_count = await self.clear_all_embeddings()
        
        # Step 7: Verify cleanup
        remaining_count = await self.verify_cleanup()
        
        # Summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n📋 TEMİZLEME RAPORU")
        print("=" * 30)
        print(f"Başlangıç embedding sayısı: {initial_count:,}")
        print(f"Silinen embedding sayısı: {deleted_count:,}")
        print(f"Kalan embedding sayısı: {remaining_count:,}")
        print(f"Toplam süre: {duration.total_seconds():.1f} saniye")
        print(f"Tamamlanma zamanı: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        success = remaining_count == 0
        print(f"\n{'✅ TEMİZLEME BAŞARILI!' if success else '❌ TEMİZLEME KISMEN BAŞARISIZ!'}")
        
        return success


async def main():
    """Ana fonksiyon"""
    cleaner = EmbeddingCleaner()
    success = await cleaner.run_cleanup()
    
    # Exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Script doğrudan çalıştırıldığında
    print("🚀 Elasticsearch Embedding Temizleme Script Başlatılıyor...")
    asyncio.run(main())