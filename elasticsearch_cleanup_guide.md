# Elasticsearch Embeddings Cleanup Guide

## Overview
`clear_elasticsearch_embeddings.py` scripti, Elasticsearch'deki document embeddings'leri güvenli bir şekilde temizlemek için tasarlanmıştır.

## Features
- ✅ Güvenli temizlik işlemleri (onay gerektiren destructive operations)
- ✅ Belirli index'leri temizleme
- ✅ Belirli document'ları silme
- ✅ Tüm embeddings'leri temizleme
- ✅ Database sync log güncelleme
- ✅ Detaylı logging ve progress tracking

## Usage Examples

### 1. Elasticsearch Durumunu Kontrol Etme
```bash
python clear_elasticsearch_embeddings.py --action info
```

**Output:**
```
============================================================
ELASTICSEARCH INDICES INFORMATION
============================================================
Index: documents
  Documents: 1,250
  Size: 45.2mb
  Status: open

Index: document_chunks
  Documents: 15,680
  Size: 892.1mb
  Status: open

Total user documents: 16,930
```

### 2. Tüm Embeddings'leri Temizleme
```bash
# WARNING: Bu komut TÜM embeddings'leri siler!
python clear_elasticsearch_embeddings.py --action clear-all --confirm
```

### 3. Belirli Bir Index'i Temizleme
```bash
# Sadece "documents" index'ini temizle
python clear_elasticsearch_embeddings.py --action clear-index --index documents --confirm

# Sadece "document_chunks" index'ini temizle  
python clear_elasticsearch_embeddings.py --action clear-index --index document_chunks --confirm
```

### 4. Belirli Document'ları Silme
```bash
# Belirli document ID'lerini sil
python clear_elasticsearch_embeddings.py --action clear-docs --doc-ids doc1 doc2 doc3 --confirm

# Belirli index'den belirli document'ları sil
python clear_elasticsearch_embeddings.py --action clear-docs --index documents --doc-ids abc123 def456 --confirm
```

### 5. Farklı Elasticsearch URL Kullanma
```bash
# Development environment
python clear_elasticsearch_embeddings.py --action info --es-url http://localhost:9200

# Production environment (default)
python clear_elasticsearch_embeddings.py --action info --es-url https://elastic.mevzuatgpt.org
```

## Safety Features

### Confirmation Requirements
Destructive operations (clear-all, clear-index) require `--confirm` flag:
```bash
# Bu komut çalışmaz - güvenlik için
python clear_elasticsearch_embeddings.py --action clear-all

# Bu komut çalışır
python clear_elasticsearch_embeddings.py --action clear-all --confirm
```

### System Index Protection
Script otomatik olarak sistem index'lerini (`.` ile başlayanlar) korur ve sadece user index'lerini işler.

### Database Integration
PostgreSQL bağlantısı varsa, temizlik işlemleri `elasticsearch_sync_log` tablosuna kaydedilir:
- Operation type: 'CLEANUP'
- Status: 'completed' / 'partial'
- Documents affected count
- Detailed operation summary

## Common Use Cases

### 1. Development Environment Reset
```bash
# Development'da tüm test data'yı temizle
python clear_elasticsearch_embeddings.py --action clear-all --confirm --es-url http://localhost:9200
```

### 2. Production Maintenance
```bash
# Önce durumu kontrol et
python clear_elasticsearch_embeddings.py --action info

# Sadece eski chunk'ları temizle
python clear_elasticsearch_embeddings.py --action clear-index --index document_chunks --confirm

# Yeni upload'lar için hazır hale getir
```

### 3. Corrupted Data Cleanup
```bash
# Bozuk document'ları tespit et ve temizle
python clear_elasticsearch_embeddings.py --action clear-docs --doc-ids corrupted1 corrupted2 --confirm
```

## Error Handling

Script aşağıdaki durumları handle eder:
- Elasticsearch connection failures
- Index not found errors
- Document not found (404) errors
- Partial deletion scenarios
- Network timeouts

## Logging

Script detaylı logging sağlar:
- INFO: Normal operations
- WARNING: Non-critical issues  
- ERROR: Critical failures

Log format:
```
2025-08-18 02:55:00 - elasticsearch_cleaner - INFO - Connected to Elasticsearch: 8.19.2
2025-08-18 02:55:01 - elasticsearch_cleaner - INFO - Found 15680 documents in document_chunks  
2025-08-18 02:55:15 - elasticsearch_cleaner - INFO - Deleted 15680 documents from document_chunks
```

## Requirements

Script dependencies:
```bash
pip install elasticsearch asyncpg
```

Environment variables:
- `DATABASE_URL`: PostgreSQL connection (optional)

## Best Practices

1. **Always check status first:**
   ```bash
   python clear_elasticsearch_embeddings.py --action info
   ```

2. **Use index-specific cleanup when possible:**
   ```bash
   # Prefer this
   python clear_elasticsearch_embeddings.py --action clear-index --index documents --confirm
   
   # Over this (unless really needed)
   python clear_elasticsearch_embeddings.py --action clear-all --confirm
   ```

3. **Monitor database sync status:**
   Check `elasticsearch_sync_log` table after cleanup operations.

4. **Test in development first:**
   Always test cleanup scripts in development before running in production.