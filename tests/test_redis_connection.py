#!/usr/bin/env python3
"""
Redis Connection Test
Redis Cloud bağlantısını ve temel operasyonları test eder
"""

import os
import sys
import redis
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RedisConnectionTest:
    def __init__(self):
        # Redis configuration from .env
        self.redis_url = os.getenv('REDIS_URL')
        self.celery_broker_url = os.getenv('CELERY_BROKER_URL')
        self.celery_result_backend = os.getenv('CELERY_RESULT_BACKEND')
        
        self.redis_client = None
        
    def check_config(self):
        """Environment variables kontrolü"""
        print("🔧 Redis environment variables kontrol ediliyor...")
        
        missing = []
        if not self.redis_url:
            missing.append('REDIS_URL')
        if not self.celery_broker_url:
            missing.append('CELERY_BROKER_URL')
        if not self.celery_result_backend:
            missing.append('CELERY_RESULT_BACKEND')
        
        if missing:
            print(f"❌ Eksik environment variables: {', '.join(missing)}")
            return False
        
        print("✅ Tüm Redis environment variables mevcut")
        print(f"🔗 REDIS_URL: {self.redis_url[:50]}...")
        print(f"📊 CELERY_BROKER_URL: {self.celery_broker_url[:50]}...")
        print(f"📋 CELERY_RESULT_BACKEND: {self.celery_result_backend[:50]}...")
        return True
    
    def test_basic_connection(self):
        """Temel Redis bağlantısı testi"""
        try:
            print("🔌 Redis temel bağlantısı test ediliyor...")
            
            # Create Redis client
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10
            )
            
            # Test ping
            response = self.redis_client.ping()
            if response:
                print("✅ Redis PING başarılı!")
                return True
            else:
                print("❌ Redis PING başarısız!")
                return False
                
        except Exception as e:
            print(f"❌ Redis bağlantı hatası: {str(e)}")
            return False
    
    def test_basic_operations(self):
        """Temel Redis operasyonları testi"""
        try:
            print("📝 Redis temel operasyonlar test ediliyor...")
            
            if not self.redis_client:
                return False
            
            # Test key
            test_key = f"mevzuatgpt_test_{int(datetime.now().timestamp())}"
            test_value = f"Test value created at {datetime.now().isoformat()}"
            
            # SET operation
            self.redis_client.set(test_key, test_value, ex=60)  # 60 seconds expiry
            print(f"✅ SET operation successful: {test_key}")
            
            # GET operation
            retrieved_value = self.redis_client.get(test_key)
            if retrieved_value == test_value:
                print(f"✅ GET operation successful: {retrieved_value[:50]}...")
            else:
                print(f"❌ GET operation failed. Expected: {test_value[:30]}..., Got: {retrieved_value}")
                return False
            
            # DELETE operation
            self.redis_client.delete(test_key)
            deleted_value = self.redis_client.get(test_key)
            if deleted_value is None:
                print("✅ DELETE operation successful")
            else:
                print(f"❌ DELETE operation failed: {deleted_value}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Redis operasyon hatası: {str(e)}")
            return False
    
    def test_celery_broker(self):
        """Celery broker bağlantısı testi"""
        try:
            print("🔄 Celery broker bağlantısı test ediliyor...")
            
            # Create separate client for Celery broker
            broker_client = redis.from_url(
                self.celery_broker_url,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10
            )
            
            # Test connection
            response = broker_client.ping()
            if response:
                print("✅ Celery broker bağlantısı başarılı!")
                
                # Test queue operations
                test_queue = "mevzuatgpt_test_queue"
                test_message = {"task": "test_task", "timestamp": datetime.now().isoformat()}
                
                # Push to queue
                broker_client.lpush(test_queue, str(test_message))
                print(f"✅ Queue PUSH successful: {test_queue}")
                
                # Pop from queue
                popped_message = broker_client.rpop(test_queue)
                if popped_message:
                    print(f"✅ Queue POP successful: {popped_message[:50]}...")
                else:
                    print("❌ Queue POP failed")
                    return False
                
                broker_client.close()
                return True
            else:
                print("❌ Celery broker PING başarısız!")
                return False
                
        except Exception as e:
            print(f"❌ Celery broker bağlantı hatası: {str(e)}")
            return False
    
    def test_result_backend(self):
        """Celery result backend bağlantısı testi"""
        try:
            print("📋 Celery result backend test ediliyor...")
            
            # Create separate client for result backend
            result_client = redis.from_url(
                self.celery_result_backend,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10
            )
            
            # Test connection
            response = result_client.ping()
            if response:
                print("✅ Celery result backend bağlantısı başarılı!")
                
                # Test result storage
                task_id = f"test_task_{int(datetime.now().timestamp())}"
                result_key = f"celery-task-meta-{task_id}"
                test_result = {
                    "status": "SUCCESS",
                    "result": "Test task completed",
                    "timestamp": datetime.now().isoformat()
                }
                
                # Store result
                result_client.set(result_key, str(test_result), ex=60)
                print(f"✅ Result storage successful: {task_id}")
                
                # Retrieve result
                stored_result = result_client.get(result_key)
                if stored_result:
                    print(f"✅ Result retrieval successful: {stored_result[:50]}...")
                else:
                    print("❌ Result retrieval failed")
                    return False
                
                # Cleanup
                result_client.delete(result_key)
                result_client.close()
                return True
            else:
                print("❌ Celery result backend PING başarısız!")
                return False
                
        except Exception as e:
            print(f"❌ Celery result backend bağlantı hatası: {str(e)}")
            return False
    
    def get_redis_info(self):
        """Redis sunucu bilgilerini al"""
        try:
            if not self.redis_client:
                return False
                
            print("ℹ️ Redis sunucu bilgileri alınıyor...")
            
            info = self.redis_client.info()
            
            print(f"📊 Redis Version: {info.get('redis_version', 'Unknown')}")
            print(f"🔌 Connected Clients: {info.get('connected_clients', 'Unknown')}")
            print(f"💾 Used Memory: {info.get('used_memory_human', 'Unknown')}")
            print(f"⏱️ Uptime: {info.get('uptime_in_seconds', 'Unknown')} seconds")
            
            return True
            
        except Exception as e:
            print(f"❌ Redis info alma hatası: {str(e)}")
            return False
    
    def cleanup(self):
        """Connection cleanup"""
        try:
            if self.redis_client:
                self.redis_client.close()
                print("🧹 Redis bağlantısı temizlendi")
        except:
            pass
    
    def run_all_tests(self):
        """Tüm testleri çalıştır"""
        print("=" * 60)
        print("🧪 Redis Connection Test Başlıyor")
        print("=" * 60)
        
        # 1. Config check
        if not self.check_config():
            return False
        
        print("\n" + "-" * 40)
        
        # 2. Basic connection test
        basic_success = self.test_basic_connection()
        if not basic_success:
            return False
        
        print("\n" + "-" * 40)
        
        # 3. Basic operations test
        ops_success = self.test_basic_operations()
        
        print("\n" + "-" * 40)
        
        # 4. Celery broker test
        broker_success = self.test_celery_broker()
        
        print("\n" + "-" * 40)
        
        # 5. Result backend test
        result_success = self.test_result_backend()
        
        print("\n" + "-" * 40)
        
        # 6. Redis info
        self.get_redis_info()
        
        # 7. Cleanup
        self.cleanup()
        
        print("\n" + "=" * 60)
        if basic_success and ops_success and broker_success and result_success:
            print("🎉 TÜM REDIS TESTLERI BAŞARILI!")
            print("✅ Redis Cloud bağlantısı tamamen çalışıyor")
            print("✅ Temel operasyonlar çalışıyor")
            print("✅ Celery broker çalışıyor")
            print("✅ Celery result backend çalışıyor")
            print("\n📝 Celery worker başlatmaya hazır!")
            return True
        else:
            print("💥 REDIS TESTLERI BAŞARISIZ!")
            print("❌ Redis Cloud bağlantı problemi var")
            return False

def main():
    """Ana test fonksiyonu"""
    test = RedisConnectionTest()
    success = test.run_all_tests()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()