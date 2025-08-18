# Elasticsearch Embeddings Temizleme Rehberi

## Genel Bakış
MevzuatGPT sisteminde Elasticsearch'deki document embeddings'leri güvenli bir şekilde temizlemek için özel script'ler hazırlanmıştır. Bu araçlar production ortamında güvenle kullanılabilir ve detaylı logging sağlar.

## Mevcut Araçlar

### 1. Ana Script: `simple_elasticsearch_cleaner.py`
HTTP tabanlı, güvenli Elasticsearch temizlik aracı.

### 2. Yardımcı Script: `run_elasticsearch_cleanup.sh`
Interactive kullanım için shell wrapper script'i.

## Elasticsearch Durumu Kontrol Etme

### Temel Durum Kontrolü
```bash
python simple_elasticsearch_cleaner.py --action info
```

**Örnek Çıktı:**
```
============================================================
ELASTICSEARCH INDICES INFORMATION
============================================================
Index: mevzuat_embeddings
  Documents: 206
  Size: 4.2mb
  Status: open

Total documents: 206
```

### Interactive Durum Kontrolü
```bash
./run_elasticsearch_cleanup.sh info
```

## Embeddings Temizleme İşlemleri

### 1. Tüm Embeddings'leri Temizleme (Dikkatli Kullanın!)

**Python Script ile:**
```bash
python simple_elasticsearch_cleaner.py --action clear-all --confirm
```

**Interactive Script ile:**
```bash
./run_elasticsearch_cleanup.sh clear-all
# "yes" yazarak onaylayın
```

⚠️ **UYARI**: Bu işlem TÜM embeddings'leri siler ve geri alınamaz!

### 2. Belirli Index Temizleme

**Mevzuat embeddings index'ini temizle:**
```bash
python simple_elasticsearch_cleaner.py --action clear-index --index mevzuat_embeddings --confirm
```

**Interactive kullanım:**
```bash
./run_elasticsearch_cleanup.sh clear-index mevzuat_embeddings
# "yes" yazarak onaylayın
```

### 3. Belirli Document'ları Silme

**Belirli document ID'lerini sil:**
```bash
python simple_elasticsearch_cleaner.py --action clear-docs --doc-ids doc123 doc456 doc789
```

**Belirli index'den belirli document'ları sil:**
```bash
python simple_elasticsearch_cleaner.py --action clear-docs --doc-ids abc123 def456 --index mevzuat_embeddings
```

## Güvenlik Özellikleri

### 1. Onay Sistemi
Destructive işlemler için `--confirm` parametresi zorunludur:
```bash
# Bu çalışmaz (güvenlik için)
python simple_elasticsearch_cleaner.py --action clear-all

# Bu çalışır
python simple_elasticsearch_cleaner.py --action clear-all --confirm
```

### 2. System Index Koruması
Script otomatik olarak sistem index'lerini (`.` ile başlayanlar) korur ve sadece kullanıcı index'lerini işler.

### 3. Database Logging
Temizlik işlemleri otomatik olarak `elasticsearch_sync_log` tablosuna kaydedilir:
- Operation type: 'CLEANUP'
- Status: 'completed' / 'partial'
- Etkilenen document sayısı
- Detaylı işlem özeti

## Farklı Ortamlar İçin Kullanım

### Development Ortamı
```bash
python simple_elasticsearch_cleaner.py --action info --es-url http://localhost:9200
```

### Production Ortamı (Varsayılan)
```bash
python simple_elasticsearch_cleaner.py --action info --es-url https://elastic.mevzuatgpt.org
```

## Yaygın Kullanım Senaryoları

### 1. Development Test Data Temizleme
```bash
# Development ortamındaki tüm test verilerini temizle
python simple_elasticsearch_cleaner.py --action clear-all --confirm --es-url http://localhost:9200
```

### 2. Production Bakım İşlemleri
```bash
# Önce durumu kontrol et
python simple_elasticsearch_cleaner.py --action info

# Sadece mevzuat embeddings'leri temizle
python simple_elasticsearch_cleaner.py --action clear-index --index mevzuat_embeddings --confirm

# Yeni upload'lar için sistemin hazır olduğunu kontrol et
python simple_elasticsearch_cleaner.py --action info
```

### 3. Bozuk Veri Temizleme
```bash
# Bozuk document'ları tespit edip temizle
python simple_elasticsearch_cleaner.py --action clear-docs --doc-ids corrupted1 corrupted2 corrupted3 --confirm
```

### 4. Sistem Yeniden Başlatma Öncesi
```bash
# Tüm embeddings'leri temizleyerek fresh start
python simple_elasticsearch_cleaner.py --action clear-all --confirm

# Yeni document upload'ları için hazır
```

## Hata Durumları ve Çözümleri

### Connection Hatası
```
ERROR - Could not connect to Elasticsearch
```
**Çözüm**: Elasticsearch URL'ini kontrol edin ve servisin çalıştığından emin olun.

### Permission Hatası
```
ERROR - Failed to clear index: HTTP 403
```
**Çözüm**: Elasticsearch authentication ayarlarını kontrol edin.

### Partial Deletion
```
WARNING - Index still has 50 documents after cleanup
```
**Çözüm**: İşlemi tekrar çalıştırın veya manuel olarak kalan document'ları kontrol edin.

## Logging ve İzleme

### Script Logs
Script detaylı logging sağlar:
```
2025-08-18 02:55:00 - INFO - Connected to Elasticsearch: 8.19.2
2025-08-18 02:55:01 - INFO - Found 206 documents in mevzuat_embeddings  
2025-08-18 02:55:15 - INFO - Successfully deleted 206 documents from 'mevzuat_embeddings'
```

### Database Logs
Temizlik işlemleri `elasticsearch_sync_log` tablosunda izlenebilir:
```sql
SELECT * FROM elasticsearch_sync_log 
WHERE operation_type = 'CLEANUP' 
ORDER BY created_at DESC;
```

## En İyi Uygulamalar

### 1. Önce Durum Kontrolü
Her zaman işlem öncesi mevcut durumu kontrol edin:
```bash
python simple_elasticsearch_cleaner.py --action info
```

### 2. Index-Specific Temizlik Tercih Edin
Mümkün olduğunca belirli index temizliği kullanın:
```bash
# Bunu tercih edin
python simple_elasticsearch_cleaner.py --action clear-index --index mevzuat_embeddings --confirm

# Bunu sadece gerektiğinde kullanın
python simple_elasticsearch_cleaner.py --action clear-all --confirm
```

### 3. Development'ta Test Edin
Production'da kullanmadan önce development ortamında test edin.

### 4. Backup Almayı Düşünün
Önemli data varsa, temizlik öncesi backup alma seçeneklerini değerlendirin.

### 5. İşlem Sonrası Kontrol
Temizlik işlemi sonrası sistem durumunu kontrol edin:
```bash
python simple_elasticsearch_cleaner.py --action info
```

## Troubleshooting

### Script Çalışmıyor
1. Python dependencies kontrol edin: `httpx`, `asyncpg`
2. Elasticsearch URL'ini doğrulayın
3. Network connectivity kontrol edin

### Beklenenden Az Document Silindi
1. Index'in read-only olmadığından emin olun
2. Elasticsearch cluster health'ini kontrol edin
3. Script'i tekrar çalıştırmayı deneyin

### Database Logging Çalışmıyor
1. `DATABASE_URL` environment variable'ını kontrol edin
2. PostgreSQL connection'ını test edin
3. `elasticsearch_sync_log` tablosunun var olduğunu kontrol edin

## İletişim ve Destek

Herhangi bir sorun yaşarsanız:
1. Script log'larını kontrol edin
2. Elasticsearch cluster durumunu kontrol edin  
3. Database connection'ını test edin
4. Gerekirse development ekibiyle iletişime geçin