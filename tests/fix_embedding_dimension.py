#!/usr/bin/env python3
"""
Supabase Embedding Dimension Fix Script
- Embedding tablosu dimension'ını 3072'ye günceller
- Eski 1536 boyutlu embedding'leri siler
- Yeni 3072 boyutlu embedding generation'ı test eder
"""

import sys
import logging
from typing import List

# Add project root to path
sys.path.append('/home/runner/workspace')

from core.supabase_client import supabase_client

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clear_all_embeddings():
    """Tüm embedding'leri temizle"""
    try:
        logger.info("🗑️ Tüm embedding'ler siliniyor...")
        
        # Count before deletion
        count_response = supabase_client.table('mevzuat_embeddings').select('id').execute()
        before_count = len(count_response.data) if count_response.data else 0
        logger.info(f"📊 Silinecek embedding sayısı: {before_count}")
        
        # Delete all embeddings
        delete_response = supabase_client.table('mevzuat_embeddings').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        
        logger.info(f"✅ {before_count} embedding silindi")
        
        # Reset all document statuses to processing for re-processing
        update_response = supabase_client.table('mevzuat_documents') \
            .update({'status': 'processing'}) \
            .eq('status', 'completed') \
            .execute()
        
        updated_count = len(update_response.data) if update_response.data else 0
        logger.info(f"🔄 {updated_count} doküman status'ü processing'e güncellendi")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Embedding temizleme hatası: {e}")
        return False

def check_embedding_table_structure():
    """Embedding tablosu structure'ını kontrol et"""
    try:
        logger.info("🔍 Embedding tablo yapısı kontrol ediliyor...")
        
        # Sample embedding test - dimension kontrolü için
        sample_response = supabase_client.table('mevzuat_embeddings').select('embedding').limit(1).execute()
        
        if sample_response.data and sample_response.data[0].get('embedding'):
            embedding = sample_response.data[0]['embedding']
            dimension = len(embedding) if isinstance(embedding, list) else 0
            logger.info(f"📏 Mevcut embedding dimension: {dimension}")
            
            if dimension == 1536:
                logger.warning("⚠️ Tablo hala 1536 boyutlu embeddings içeriyor")
                return "1536"
            elif dimension == 3072:
                logger.info("✅ Tablo 3072 boyutlu embeddings kullanıyor")
                return "3072"
            else:
                logger.warning(f"❓ Bilinmeyen dimension: {dimension}")
                return "unknown"
        else:
            logger.info("📋 Embedding tablosu boş")
            return "empty"
            
    except Exception as e:
        logger.error(f"❌ Tablo structure kontrolü hatası: {e}")
        return "error"

def get_supabase_sql_commands():
    """Supabase'de çalıştırılması gereken SQL komutları"""
    sql_commands = [
        "-- 1. Mevcut embedding constraint'ini kaldır",
        "ALTER TABLE mevzuat_embeddings DROP CONSTRAINT IF EXISTS mevzuat_embeddings_embedding_check;",
        "",
        "-- 2. Embedding kolonunu yeni dimension ile güncelle", 
        "ALTER TABLE mevzuat_embeddings ALTER COLUMN embedding TYPE vector(3072);",
        "",
        "-- 3. Tüm eski embedding'leri temizle (opsiyonel)",
        "DELETE FROM mevzuat_embeddings;",
        "",
        "-- 4. Doküman status'larını reset et",
        "UPDATE mevzuat_documents SET status = 'processing' WHERE status = 'completed';",
        "",
        "-- 5. Yeni constraint ekle (opsiyonel)",
        "ALTER TABLE mevzuat_embeddings ADD CONSTRAINT mevzuat_embeddings_embedding_check CHECK (array_length(embedding, 1) = 3072);"
    ]
    
    return "\n".join(sql_commands)

def main():
    """Ana işlem"""
    logger.info("🔧 SUPABASE EMBEDDİNG DİMENSİON FİX ARACI")
    logger.info("=" * 45)
    
    # 1. Mevcut durum tespiti
    logger.info("1️⃣ Mevcut embedding yapısı kontrol ediliyor...")
    current_dimension = check_embedding_table_structure()
    
    if current_dimension == "1536":
        logger.warning("⚠️ KRİTİK PROBLEM: Tablo 1536 boyut kullanıyor")
        logger.warning("   Yeni model 3072 boyut üretiyor - uyumsuzluk var!")
        
        # 2. Çözüm seçenekleri
        logger.info("\n2️⃣ ÇÖZÜM SEÇENEKLERİ:")
        logger.info("   A) Otomatik: Tüm embeddings sil, yeniden oluştur")
        logger.info("   B) Manuel: Supabase SQL Editor'da tablo yapısını güncelle")
        
        choice = input("\nSeçiminiz (A/B): ").upper().strip()
        
        if choice == "A":
            logger.info("3️⃣ Otomatik temizlik başlatılıyor...")
            if clear_all_embeddings():
                logger.info("✅ Embedding'ler temizlendi")
                logger.info("🚀 Şimdi tests/celery_restart_and_process.py çalıştır")
            else:
                logger.error("❌ Otomatik temizlik başarısız")
                
        elif choice == "B":
            logger.info("3️⃣ Manuel SQL komutları:")
            print("\n" + "="*60)
            print("SUPABASE SQL EDITOR'DA ÇALIŞTIR:")
            print("="*60)
            print(get_supabase_sql_commands())
            print("="*60)
            
            logger.info("📋 Bu komutları Supabase Dashboard > SQL Editor'da çalıştır")
            logger.info("🚀 Sonra tests/celery_restart_and_process.py çalıştır")
        
        else:
            logger.info("❌ Geçersiz seçim - çıkılıyor")
    
    elif current_dimension == "3072":
        logger.info("✅ Embedding dimension zaten doğru (3072)")
        logger.info("🚀 Direkt tests/celery_restart_and_process.py çalıştırabilirsin")
        
    elif current_dimension == "empty":
        logger.info("📋 Embedding tablosu boş - yeni embeddings 3072 boyutlu olacak")
        logger.info("🚀 tests/celery_restart_and_process.py çalıştır")
        
    else:
        logger.error(f"❌ Dimension kontrolü başarısız: {current_dimension}")

if __name__ == "__main__":
    main()