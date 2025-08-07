#!/usr/bin/env python3
"""
Celery Health Check Tool
Redis ve Celery sistem durumunu kapsamlı olarak test eder ve raporlar
"""

import os
import sys
import time
import redis
from datetime import datetime
from dotenv import load_dotenv
from celery import Celery
from typing import Dict, Any, List, Optional

# Load environment variables
load_dotenv()

class CeleryHealthChecker:
    """Celery ve Redis sağlık kontrolcüsü"""
    
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL')
        self.celery_broker_url = os.getenv('CELERY_BROKER_URL')
        self.celery_result_backend = os.getenv('CELERY_RESULT_BACKEND')
        
        # Redis clients
        self.redis_client = None
        
        # Celery app for inspection
        self.celery_app = Celery('mevzuat_gpt')
        self.celery_app.config_from_object('tasks.celery_app')
        self.inspect = self.celery_app.control.inspect()
        
        # Test results
        self.test_results: Dict[str, Dict[str, Any]] = {}
    
    def log_test_result(self, test_name: str, success: bool, details: str = "", data: Any = None):
        """Test sonucunu kaydet"""
        self.test_results[test_name] = {
            'success': success,
            'details': details,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
    
    def test_redis_basic_connection(self) -> bool:
        """Redis temel bağlantı testi"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10
            )
            
            response = self.redis_client.ping()
            if response:
                info = self.redis_client.info()
                details = f"Redis {info.get('redis_version', 'Unknown')} - {info.get('connected_clients', 0)} clients"
                self.log_test_result("redis_connection", True, details, info)
                return True
            else:
                self.log_test_result("redis_connection", False, "PING failed")
                return False
                
        except Exception as e:
            self.log_test_result("redis_connection", False, f"Connection error: {str(e)}")
            return False
    
    def test_redis_operations(self) -> bool:
        """Redis operasyon testleri"""
        try:
            if not self.redis_client:
                return False
            
            # Test key operations
            test_key = f"health_check_{int(time.time())}"
            test_value = f"test_value_{datetime.now().isoformat()}"
            
            # SET/GET/DELETE test
            self.redis_client.set(test_key, test_value, ex=30)
            retrieved = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)
            
            success = retrieved == test_value
            details = "SET/GET/DELETE operations successful" if success else "Operation mismatch"
            self.log_test_result("redis_operations", success, details)
            return success
            
        except Exception as e:
            self.log_test_result("redis_operations", False, f"Operation error: {str(e)}")
            return False
    
    def test_celery_broker(self) -> bool:
        """Celery broker bağlantı testi"""
        try:
            broker_client = redis.from_url(
                self.celery_broker_url,
                decode_responses=True,
                socket_timeout=10
            )
            
            response = broker_client.ping()
            if response:
                # Test queue operations
                test_queue = f"health_check_queue_{int(time.time())}"
                test_message = {"task": "health_check", "timestamp": datetime.now().isoformat()}
                
                broker_client.lpush(test_queue, str(test_message))
                popped = broker_client.rpop(test_queue)
                
                success = popped is not None
                details = "Broker connection and queue operations successful" if success else "Queue operations failed"
                self.log_test_result("celery_broker", success, details)
                
                broker_client.close()
                return success
            else:
                self.log_test_result("celery_broker", False, "Broker PING failed")
                return False
                
        except Exception as e:
            self.log_test_result("celery_broker", False, f"Broker error: {str(e)}")
            return False
    
    def test_celery_workers(self) -> bool:
        """Celery worker durumu testi"""
        try:
            # Check active workers
            active_workers = self.inspect.active()
            registered_tasks = self.inspect.registered()
            stats = self.inspect.stats()
            
            if not active_workers:
                self.log_test_result("celery_workers", False, "No active workers found")
                return False
            
            worker_count = len(active_workers)
            worker_details = []
            
            for worker_name, tasks in active_workers.items():
                worker_info = {
                    'name': worker_name,
                    'active_tasks': len(tasks),
                    'registered_task_count': len(registered_tasks.get(worker_name, [])) if registered_tasks else 0
                }
                
                if stats and worker_name in stats:
                    worker_stats = stats[worker_name]
                    worker_info['total_tasks_processed'] = sum(
                        count for task_name, count in worker_stats.get('total', {}).items()
                        if 'process_document' in task_name
                    )
                    worker_info['pool_implementation'] = worker_stats.get('pool', {}).get('implementation', 'Unknown')
                
                worker_details.append(worker_info)
            
            details = f"{worker_count} active workers found"
            self.log_test_result("celery_workers", True, details, worker_details)
            return True
            
        except Exception as e:
            self.log_test_result("celery_workers", False, f"Worker check error: {str(e)}")
            return False
    
    def test_celery_ping(self) -> bool:
        """Celery worker ping testi"""
        try:
            pong_responses = self.inspect.ping()
            
            if pong_responses:
                responsive_workers = len(pong_responses)
                worker_names = list(pong_responses.keys())
                details = f"{responsive_workers} workers responding to ping"
                self.log_test_result("celery_ping", True, details, worker_names)
                return True
            else:
                self.log_test_result("celery_ping", False, "No workers responding to ping")
                return False
                
        except Exception as e:
            self.log_test_result("celery_ping", False, f"Ping error: {str(e)}")
            return False
    
    def test_queue_status(self) -> bool:
        """Queue durumu testi"""
        try:
            reserved = self.inspect.reserved()
            scheduled = self.inspect.scheduled()
            
            total_reserved = 0
            total_scheduled = 0
            
            if reserved:
                total_reserved = sum(len(tasks) for tasks in reserved.values())
            
            if scheduled:
                total_scheduled = sum(len(tasks) for tasks in scheduled.values())
            
            queue_info = {
                'reserved_tasks': total_reserved,
                'scheduled_tasks': total_scheduled,
                'queue_details': reserved if reserved else {}
            }
            
            details = f"Reserved: {total_reserved}, Scheduled: {total_scheduled}"
            self.log_test_result("queue_status", True, details, queue_info)
            return True
            
        except Exception as e:
            self.log_test_result("queue_status", False, f"Queue check error: {str(e)}")
            return False
    
    def cleanup_connections(self):
        """Bağlantıları temizle"""
        try:
            if self.redis_client:
                self.redis_client.close()
        except:
            pass
    
    def print_health_report(self):
        """Sağlık raporu yazdır"""
        print("=" * 70)
        print("🏥 CELERY & REDIS SAĞLIK RAPORU")
        print("=" * 70)
        print(f"🕐 Rapor Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Calculate overall health
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result['success'])
        health_percentage = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Print summary
        if health_percentage >= 90:
            status_icon = "🟢"
            status_text = "MÜKEMMEL"
        elif health_percentage >= 70:
            status_icon = "🟡"
            status_text = "İYİ"
        elif health_percentage >= 50:
            status_icon = "🟠"
            status_text = "UYARI"
        else:
            status_icon = "🔴"
            status_text = "KRİTİK"
        
        print(f"{status_icon} GENEL DURUM: {status_text} ({health_percentage:.1f}%)")
        print(f"📊 Test Sonuçları: {successful_tests}/{total_tests} başarılı")
        print()
        
        # Detailed test results
        for test_name, result in self.test_results.items():
            icon = "✅" if result['success'] else "❌"
            test_display_name = test_name.replace('_', ' ').title()
            
            print(f"{icon} {test_display_name}")
            if result['details']:
                print(f"   📝 {result['details']}")
            
            # Print additional data for some tests
            if result['success'] and result['data']:
                if test_name == "celery_workers" and isinstance(result['data'], list):
                    for worker in result['data']:
                        print(f"   👷 {worker['name']}: {worker['active_tasks']} aktif task")
                        if 'total_tasks_processed' in worker:
                            print(f"      📈 Toplam işlenen: {worker['total_tasks_processed']} task")
                
                elif test_name == "redis_connection" and isinstance(result['data'], dict):
                    print(f"   💾 Memory: {result['data'].get('used_memory_human', 'Unknown')}")
                    print(f"   ⏱️ Uptime: {result['data'].get('uptime_in_seconds', 0)} seconds")
            
            print()
        
        # Recommendations
        print("💡 ÖNERİLER:")
        if health_percentage < 100:
            failed_tests = [name for name, result in self.test_results.items() if not result['success']]
            for test_name in failed_tests:
                if test_name == "redis_connection":
                    print("   🔧 Redis bağlantı ayarlarını kontrol edin")
                elif test_name == "celery_workers":
                    print("   🔧 Celery worker'ları başlatın: celery -A tasks.celery_app worker")
                elif test_name == "celery_broker":
                    print("   🔧 CELERY_BROKER_URL environment variable'ını kontrol edin")
        else:
            print("   🎉 Tüm sistemler operasyonel - herhangi bir aksiyon gerekmiyor!")
        
        print()
        print("=" * 70)
    
    def run_comprehensive_health_check(self) -> bool:
        """Kapsamlı sağlık kontrolü çalıştır"""
        print("🔍 Kapsamlı sağlık kontrolü başlıyor...")
        print()
        
        # Run all tests
        tests = [
            ("Redis Bağlantısı", self.test_redis_basic_connection),
            ("Redis Operasyonları", self.test_redis_operations),
            ("Celery Broker", self.test_celery_broker),
            ("Celery Workers", self.test_celery_workers),
            ("Celery Ping", self.test_celery_ping),
            ("Queue Durumu", self.test_queue_status)
        ]
        
        for test_description, test_function in tests:
            print(f"⏳ {test_description} test ediliyor...")
            test_function()
            time.sleep(0.5)  # Small delay between tests
        
        # Cleanup
        self.cleanup_connections()
        
        # Print comprehensive report
        self.print_health_report()
        
        # Return overall success
        successful_tests = sum(1 for result in self.test_results.values() if result['success'])
        return successful_tests == len(self.test_results)

def main():
    """Ana sağlık kontrolü fonksiyonu"""
    checker = CeleryHealthChecker()
    
    try:
        is_healthy = checker.run_comprehensive_health_check()
        
        if is_healthy:
            print("🎯 Sonuç: Sistem tamamen sağlıklı!")
            sys.exit(0)
        else:
            print("⚠️ Sonuç: Sistemde problemler tespit edildi.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Sağlık kontrolü kullanıcı tarafından iptal edildi.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Beklenmeyen hata: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()