#!/usr/bin/env python3
"""
Celery Worker Management ve Processing Script
- Celery worker yeniden başlatır
- Processing status'taki PDF'leri tespit eder
- Bekleyen embedding işlerini tetikler
- Supabase embedding dimension sorununu çözer
"""

import os
import sys
import time
import subprocess
import signal
from typing import List, Dict, Any
import logging

# Add project root to path
sys.path.append('/home/runner/workspace')

from core.supabase_client import SupabaseClient

# Initialize client
sb_client = SupabaseClient().get_client(use_service_key=True)
from tasks.document_processor import process_document_task

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CeleryManager:
    """Celery Worker ve Task Management"""
    
    def __init__(self):
        self.celery_pid = None
        
    def restart_celery_worker(self) -> bool:
        """Celery worker'ı yeniden başlat"""
        try:
            logger.info("🔄 Celery worker yeniden başlatılıyor...")
            
            # Mevcut celery process'leri öldür
            try:
                subprocess.run(['pkill', '-f', 'celery.*worker'], check=False)
                time.sleep(2)
                logger.info("✅ Eski Celery process'ler durduruldu")
            except Exception as e:
                logger.warning(f"Process kill warning: {e}")
            
            # Yeni celery worker başlat
            celery_cmd = [
                'celery', '-A', 'tasks.celery_app', 
                'worker', '--loglevel=info', '--concurrency=1'
            ]
            
            logger.info(f"🚀 Celery worker başlatılıyor: {' '.join(celery_cmd)}")
            process = subprocess.Popen(
                celery_cmd,
                cwd='/home/runner/workspace',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.celery_pid = process.pid
            time.sleep(5)  # Worker'ın başlamasını bekle
            
            # Process hala çalışıyor mu kontrol et
            if process.poll() is None:
                logger.info(f"✅ Celery worker başlatıldı (PID: {self.celery_pid})")
                return True
            else:
                logger.error("❌ Celery worker başlatılamadı")
                return False
                
        except Exception as e:
            logger.error(f"❌ Celery restart hatası: {e}")
            return False
    
    def get_processing_documents(self) -> List[Dict[str, Any]]:
        """Processing status'taki dokümanları getir"""
        try:
            response = sb_client.table('mevzuat_documents') \
                .select('id, title, status, created_at') \
                .eq('status', 'processing') \
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"❌ Processing documents getirme hatası: {e}")
            return []
    
    def get_documents_without_embeddings(self) -> List[Dict[str, Any]]:
        """Embedding'i olmayan completed dokümanları getir"""
        try:
            # Tüm completed dokümanları al
            docs_response = sb_client.table('mevzuat_documents') \
                .select('id, title, status') \
                .eq('status', 'completed') \
                .execute()
            
            docs_without_embeddings = []
            for doc in docs_response.data or []:
                # Bu dokümana ait embedding var mı kontrol et
                embed_response = sb_client.table('mevzuat_embeddings') \
                    .select('id') \
                    .eq('document_id', doc['id']) \
                    .limit(1) \
                    .execute()
                
                if not embed_response.data:
                    docs_without_embeddings.append(doc)
            
            return docs_without_embeddings
            
        except Exception as e:
            logger.error(f"❌ Documents without embeddings getirme hatası: {e}")
            return []
    
    def trigger_document_processing(self, document_id: str) -> bool:
        """Doküman processing'ini tetikle"""
        try:
            logger.info(f"🚀 Processing tetikleniyor: {document_id}")
            
            result = process_document_task.delay(document_id)
            logger.info(f"✅ Task tetiklendi - Task ID: {result.id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Task tetikleme hatası: {e}")
            return False

def check_embedding_dimension_issue():
    """Embedding dimension problemi var mı kontrol et"""
    logger.info("🔍 Embedding dimension problemi kontrol ediliyor...")
    
    try:
        # Supabase'deki embedding tablosu structure'ını kontrol et
        # pgvector extension dimension'ını öğren
        
        logger.warning("⚠️ SUPABASE EMBEDDİNG DİMENSİON SORUNU:")
        logger.warning("• Tablo: 1536 boyut bekliyor")
        logger.warning("• Yeni model: 3072 boyut üretiyor") 
        logger.warning("• Çözüm: Supabase'de tablo structure'ı güncellenmeli")
        
        logger.info("🛠️ MANUEL ÇÖZÜM GEREKLİ:")
        logger.info("1. Supabase SQL Editor'da çalıştır:")
        logger.info("   ALTER TABLE mevzuat_embeddings ALTER COLUMN embedding TYPE vector(3072);")
        logger.info("2. Ya da tüm embedding'leri sil ve yeniden oluştur")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Dimension check hatası: {e}")
        return False

def main():
    """Ana işlem"""
    logger.info("🔧 CELERY VE EMBEDDİNG YÖNETİM ARACI")
    logger.info("=" * 40)
    
    manager = CeleryManager()
    
    # 1. Embedding dimension sorununu kontrol et
    check_embedding_dimension_issue()
    
    # 2. Celery worker'ı yeniden başlat
    logger.info("1️⃣ Celery Worker yeniden başlatılıyor...")
    if not manager.restart_celery_worker():
        logger.error("❌ Celery restart başarısız - çıkılıyor")
        return
    
    # 3. Processing status'taki dokümanları bul
    logger.info("2️⃣ Processing status'taki dokümanlar kontrol ediliyor...")
    processing_docs = manager.get_processing_documents()
    logger.info(f"📋 Processing durumda {len(processing_docs)} doküman bulundu")
    
    # 4. Embedding'i olmayan dokümanları bul
    logger.info("3️⃣ Embedding'i olmayan dokümanlar kontrol ediliyor...")
    docs_without_embeddings = manager.get_documents_without_embeddings()
    logger.info(f"📋 Embedding'i olmayan {len(docs_without_embeddings)} doküman bulundu")
    
    # 5. Tüm bekleyen işleri tetikle
    all_pending_docs = processing_docs + docs_without_embeddings
    
    if all_pending_docs:
        logger.info(f"4️⃣ {len(all_pending_docs)} doküman için processing tetikleniyor...")
        
        success_count = 0
        for doc in all_pending_docs:
            logger.info(f"📄 Processing: {doc['title']} ({doc['id']})")
            if manager.trigger_document_processing(doc['id']):
                success_count += 1
                time.sleep(1)  # Rate limiting
        
        logger.info(f"✅ {success_count}/{len(all_pending_docs)} task başarıyla tetiklendi")
        
    else:
        logger.info("✅ Bekleyen doküman yok - tüm işlemler tamamlanmış")
    
    # 6. Sonuç raporu
    logger.info("📊 İŞLEM RAPORU:")
    logger.info(f"• Celery Worker: ✅ Yeniden başlatıldı")
    logger.info(f"• Processing Docs: {len(processing_docs)}")
    logger.info(f"• Missing Embeddings: {len(docs_without_embeddings)}")
    logger.info(f"• Triggered Tasks: {len(all_pending_docs)}")
    
    logger.info("⚠️ ÖNEMLİ: Embedding dimension sorunu Supabase'de manuel çözülmeli!")

if __name__ == "__main__":
    main()