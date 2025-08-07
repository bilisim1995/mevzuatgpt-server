#!/usr/bin/env python3
"""
Celery Status Checker
Celery worker durumunu, aktif task'ları ve bağlantı durumunu kontrol eder
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from celery import Celery
from celery.events.state import State
from celery.events import EventReceiver
import json

# Load environment variables
load_dotenv()

class CeleryStatusChecker:
    def __init__(self):
        self.broker_url = os.getenv('CELERY_BROKER_URL')
        self.result_backend = os.getenv('CELERY_RESULT_BACKEND')
        
        # Initialize Celery app for inspection
        self.app = Celery('mevzuat_gpt')
        self.app.config_from_object('tasks.celery_app')
        
        # Get inspector
        self.inspect = self.app.control.inspect()
    
    def check_workers(self):
        """Aktif worker'ları listele"""
        try:
            print("🔍 Aktif Celery Worker'ları kontrol ediliyor...")
            
            # Get active workers
            active_workers = self.inspect.active()
            registered_tasks = self.inspect.registered()
            stats = self.inspect.stats()
            
            if not active_workers:
                print("❌ Aktif worker bulunamadı!")
                return False
            
            print(f"✅ {len(active_workers)} aktif worker bulundu:")
            
            for worker_name, tasks in active_workers.items():
                print(f"\n📊 Worker: {worker_name}")
                print(f"   📝 Aktif Task Sayısı: {len(tasks)}")
                
                if tasks:
                    print("   🔄 Çalışan Task'lar:")
                    for task in tasks:
                        print(f"      - {task['name']} (ID: {task['id'][:8]}...)")
                        print(f"        Args: {task.get('args', [])}")
                        print(f"        Started: {task.get('time_start', 'N/A')}")
                
                # Worker istatistikleri
                if stats and worker_name in stats:
                    worker_stats = stats[worker_name]
                    print(f"   📈 Total Tasks: {worker_stats.get('total', {}).get('tasks.process_document_task', 0)}")
                    print(f"   🔗 Pool: {worker_stats.get('pool', {}).get('implementation', 'Unknown')}")
                
                # Kayıtlı task'lar
                if registered_tasks and worker_name in registered_tasks:
                    worker_tasks = registered_tasks[worker_name]
                    print(f"   📋 Kayıtlı Task Tipleri: {len(worker_tasks)}")
                    for task_name in worker_tasks[:5]:  # İlk 5 tanesi
                        print(f"      - {task_name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Worker kontrolü başarısız: {str(e)}")
            return False
    
    def check_queues(self):
        """Queue durumlarını kontrol et"""
        try:
            print("\n📋 Queue durumları kontrol ediliyor...")
            
            # Reserved tasks (queue'da bekleyen)
            reserved = self.inspect.reserved()
            scheduled = self.inspect.scheduled()
            
            total_reserved = 0
            if reserved:
                for worker_name, tasks in reserved.items():
                    task_count = len(tasks)
                    total_reserved += task_count
                    print(f"📦 {worker_name}: {task_count} task queue'da bekliyor")
                    
                    if tasks:
                        for task in tasks[:3]:  # İlk 3 task
                            print(f"   - {task['name']} (ID: {task['id'][:8]}...)")
            
            if scheduled:
                print("\n⏰ Zamanlanmış Task'lar:")
                for worker_name, tasks in scheduled.items():
                    print(f"📅 {worker_name}: {len(tasks)} zamanlanmış task")
            
            print(f"\n📊 Toplam bekleyen task: {total_reserved}")
            return True
            
        except Exception as e:
            print(f"❌ Queue kontrolü başarısız: {str(e)}")
            return False
    
    def check_broker_connection(self):
        """Broker bağlantısını test et"""
        try:
            print("\n🔗 Broker bağlantısı test ediliyor...")
            
            # Ping all workers
            pong = self.inspect.ping()
            
            if pong:
                print("✅ Broker bağlantısı aktif!")
                for worker_name, response in pong.items():
                    print(f"   🏓 {worker_name}: {response}")
                return True
            else:
                print("❌ Broker'a bağlantı yok!")
                return False
                
        except Exception as e:
            print(f"❌ Broker bağlantı testi başarısız: {str(e)}")
            return False
    
    def get_task_history(self):
        """Son task geçmişini al"""
        try:
            print("\n📈 Task istatistikleri alınıyor...")
            
            stats = self.inspect.stats()
            
            if stats:
                for worker_name, worker_stats in stats.items():
                    print(f"\n📊 {worker_name} İstatistikleri:")
                    
                    # Total task counts
                    total_stats = worker_stats.get('total', {})
                    for task_name, count in total_stats.items():
                        if 'process_document' in task_name:
                            print(f"   📝 {task_name}: {count} kez çalıştı")
                    
                    # Pool info
                    pool_info = worker_stats.get('pool', {})
                    print(f"   🔧 Pool Implementation: {pool_info.get('implementation', 'Unknown')}")
                    print(f"   👥 Processes: {pool_info.get('max-concurrency', 'Unknown')}")
                    
                    # Rusage if available
                    rusage = worker_stats.get('rusage', {})
                    if rusage:
                        print(f"   ⏱️ User Time: {rusage.get('utime', 0):.2f}s")
                        print(f"   🖥️ System Time: {rusage.get('stime', 0):.2f}s")
            
            return True
            
        except Exception as e:
            print(f"❌ Task istatistikleri alınamadı: {str(e)}")
            return False
    
    def run_full_check(self):
        """Tüm kontrolleri çalıştır"""
        print("=" * 60)
        print("🔍 Celery Durum Kontrolü")
        print("=" * 60)
        print(f"🕐 Kontrol zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 Broker URL: {self.broker_url[:50]}...")
        print(f"📋 Result Backend: {self.result_backend[:50]}...")
        
        # Run all checks
        worker_status = self.check_workers()
        print("\n" + "-" * 40)
        
        broker_status = self.check_broker_connection()
        print("\n" + "-" * 40)
        
        queue_status = self.check_queues()
        print("\n" + "-" * 40)
        
        stats_status = self.get_task_history()
        
        print("\n" + "=" * 60)
        if worker_status and broker_status:
            print("🎉 CELERY DURUMU: ÇALIŞIYOR")
            print("✅ Worker'lar aktif")
            print("✅ Broker bağlantısı sağlam")
            print("✅ Task'lar işlenebilir")
        else:
            print("⚠️ CELERY DURUMU: SORUN VAR")
            if not worker_status:
                print("❌ Worker problemi")
            if not broker_status:
                print("❌ Broker bağlantı problemi")
        
        return worker_status and broker_status

def main():
    """Ana kontrol fonksiyonu"""
    checker = CeleryStatusChecker()
    success = checker.run_full_check()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()