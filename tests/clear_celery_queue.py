#!/usr/bin/env python3
"""
Celery Queue Temizleyici
Bekleyen ve aktif olan tüm Celery task'larını temizler
"""

import os
import sys
import redis
from celery import Celery
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def clear_all_celery_tasks():
    """Tüm Celery task'larını temizle"""
    try:
        print("=" * 60)
        print("🧹 Celery Queue Temizleme İşlemi Başlıyor")
        print("=" * 60)
        print(f"🕐 Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Redis bağlantısı
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            print("❌ REDIS_URL bulunamadı!")
            return False
        
        print("🔗 Redis'e bağlanılıyor...")
        r = redis.from_url(redis_url)
        
        # Celery app
        app = Celery('mevzuat_gpt')
        app.config_from_object('tasks.celery_app')
        
        print("📊 Mevcut durum kontrol ediliyor...")
        
        # Aktif worker'ları kontrol et
        inspect = app.control.inspect()
        active_tasks = inspect.active()
        reserved_tasks = inspect.reserved()
        scheduled_tasks = inspect.scheduled()
        
        if active_tasks:
            print(f"⚠️ Aktif task'lar bulundu: {len(active_tasks)}")
            for worker, tasks in active_tasks.items():
                print(f"   👷 {worker}: {len(tasks)} aktif task")
        
        if reserved_tasks:
            print(f"⚠️ Reserved task'lar bulundu: {len(reserved_tasks)}")
            for worker, tasks in reserved_tasks.items():
                print(f"   📋 {worker}: {len(tasks)} reserved task")
        
        if scheduled_tasks:
            print(f"⚠️ Scheduled task'lar bulundu: {len(scheduled_tasks)}")
            for worker, tasks in scheduled_tasks.items():
                print(f"   ⏰ {worker}: {len(tasks)} scheduled task")
        
        print()
        print("🧹 Queue temizleme işlemi başlıyor...")
        
        # 1. Redis queue'ları temizle
        print("📭 Redis queue'ları temizleniyor...")
        
        # Celery default queue'ları
        queue_keys = [
            'celery',           # Default queue
            '_kombu.binding.celery',
            '_kombu.binding.celery.pidbox',
            'unacked',
            'unacked_index'
        ]
        
        cleared_queues = 0
        for queue_key in queue_keys:
            try:
                deleted = r.delete(queue_key)
                if deleted:
                    print(f"   ✅ {queue_key} temizlendi")
                    cleared_queues += 1
                else:
                    print(f"   ℹ️ {queue_key} zaten boş")
            except Exception as e:
                print(f"   ❌ {queue_key} temizlenemedi: {str(e)}")
        
        # 2. Celery result backend temizle
        print("📊 Result backend temizleniyor...")
        try:
            # Celery result key'lerini bul ve temizle
            pattern = "celery-task-meta-*"
            keys = r.keys(pattern)
            if keys:
                deleted = r.delete(*keys)
                print(f"   ✅ {len(keys)} result key temizlendi")
            else:
                print("   ℹ️ Result backend zaten boş")
        except Exception as e:
            print(f"   ❌ Result backend temizlenemedi: {str(e)}")
        
        # 3. Worker'ları yeniden başlat (soft restart)
        print("🔄 Worker'lar yeniden başlatılıyor...")
        try:
            app.control.pool_restart()
            print("   ✅ Worker pool restart komutu gönderildi")
        except Exception as e:
            print(f"   ❌ Worker restart başarısız: {str(e)}")
        
        # 4. Final durum kontrolü
        print()
        print("📊 Temizleme sonrası durum:")
        
        # Queue boyutlarını kontrol et
        for queue_key in ['celery']:
            try:
                size = r.llen(queue_key)
                print(f"   📭 {queue_key}: {size} task")
            except:
                print(f"   📭 {queue_key}: 0 task")
        
        print()
        print("=" * 60)
        print("✅ Celery Queue Temizleme Tamamlandı!")
        print(f"🧹 {cleared_queues} queue temizlendi")
        print("🔄 Worker'lar yeniden başlatıldı")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Queue temizleme hatası: {str(e)}")
        return False

def main():
    """Ana fonksiyon"""
    try:
        success = clear_all_celery_tasks()
        
        if success:
            print("\n🎯 Sonuç: Queue temizleme başarılı!")
            print("💡 Öneriler:")
            print("   • Yeni task'lar artık temiz queue'da çalışacak")
            print("   • Bekleyen belgeler yeniden işlenecek")
            print("   • Worker performance artacak")
            sys.exit(0)
        else:
            print("\n⚠️ Sonuç: Queue temizlemede problemler var.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ İşlem kullanıcı tarafından iptal edildi.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Beklenmeyen hata: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()