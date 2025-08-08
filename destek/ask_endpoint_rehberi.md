# MevzuatGPT Soru Sorma Endpoint Rehberi

## API Endpoint

**URL**: `POST /api/user/ask`  
**Authentication**: Bearer Token gerekli  
**Rate Limit**: 30 istek/dakika per kullanıcı

## Endpoint Özellikleri

✅ **Tam RAG Pipeline**: Embedding → Arama → AI Cevap  
✅ **Redis Cache**: Performance optimizasyonu  
✅ **Rate Limiting**: Abuse protection  
✅ **Institution Filter**: Kurum bazında filtreleme  
✅ **Confidence Score**: Cevap güvenilirlik puanı  
✅ **Search History**: Kullanıcı arama geçmişi  
✅ **Multi-AI Support**: Groq/OpenAI/Ollama

## Request Formatı

### Zorunlu Alanlar
```json
{
  "query": "Soru metni (string, minimum 3 karakter)"
}
```

### Opsiyonel Alanlar
```json
{
  "query": "Hukuki soru buraya",
  "institution_filter": "kurum_adi",
  "limit": 5,
  "similarity_threshold": 0.7,
  "use_cache": true
}
```

### Parametre Açıklamaları
- **query**: Sorulacak soru (zorunlu, min 3 karakter)
- **institution_filter**: Belirli kuruma ait belgelerle sınırla (opsiyonel)
- **limit**: Kaç kaynak dönsün (varsayılan: 5, max: 10)
- **similarity_threshold**: Benzerlik eşiği (varsayılan: 0.7, 0-1 arası)
- **use_cache**: Cache kullanılsın mı (varsayılan: true)

## Response Formatı

### Başarılı Yanıt
```json
{
  "success": true,
  "data": {
    "answer": "AI tarafından üretilen cevap",
    "sources": [
      {
        "document_title": "Belge Başlığı",
        "institution": "Kurum Adı",
        "chunk_text": "İlgili metin parçası",
        "similarity_score": 0.85,
        "page_number": 15,
        "document_url": "https://cdn.example.com/doc.pdf"
      }
    ],
    "confidence_score": 0.82,
    "model_used": "llama3-8b-8192",
    "processing_time": {
      "embedding_time": 456,
      "search_time": 123,
      "ai_time": 432,
      "total_time": 1011
    },
    "cached": false,
    "query_id": "unique_query_id"
  }
}
```

### Hata Yanıtları

#### Rate Limit Aşımı (429)
```json
{
  "success": false,
  "error": {
    "message": "Rate limit exceeded",
    "detail": "Maximum 30 requests per minute allowed",
    "code": "RATE_LIMIT_EXCEEDED"
  },
  "retry_after": 60
}
```

#### Geçersiz İstek (400)
```json
{
  "success": false,
  "error": {
    "message": "Invalid request",
    "detail": "Query must be at least 3 characters long",
    "code": "VALIDATION_ERROR"
  }
}
```

#### Yetkisiz Erişim (401)
```json
{
  "success": false,
  "error": {
    "message": "Authentication required",
    "detail": "Valid Bearer token required",
    "code": "UNAUTHORIZED"
  }
}
```

## Postman Örnek İstek

### 1. Authentication Token Al

Önce `/api/auth/login` endpoint'ine istek at:

```http
POST {{base_url}}/api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

Response'dan `access_token`'ı al.

### 2. Soru Sorma İsteği

```http
POST {{base_url}}/api/user/ask
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "query": "Kişisel verilerin işlenmesinde hangi prensipler uygulanmalıdır?",
  "limit": 3,
  "similarity_threshold": 0.75,
  "use_cache": true
}
```

### 3. Kuruma Özel Arama

```http
POST {{base_url}}/api/user/ask
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "query": "İş güvenliği mevzuatı nedir?",
  "institution_filter": "Çalışma ve Sosyal Güvenlik Bakanlığı",
  "limit": 5
}
```

## Postman Collection Variables

Postman'de bu değişkenleri tanımla:

```json
{
  "base_url": "http://0.0.0.0:5000",
  "access_token": "Bearer_token_buraya"
}
```

## Performance Metrikleri

- **Embedding**: ~500-1000ms (OpenAI API)
- **Vector Search**: ~50-200ms (Supabase)
- **AI Response**: ~300-500ms (Groq)
- **Total Pipeline**: ~1000-1500ms
- **Cache Hit**: ~50-100ms

## Kullanım Örnekleri

### Basit Soru
```bash
curl -X POST "http://0.0.0.0:5000/api/user/ask" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "KVKK nedir?"}'
```

### Detaylı Soru
```bash
curl -X POST "http://0.0.0.0:5000/api/user/ask" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Şirket kuruluş işlemleri nasıl yapılır?",
    "limit": 5,
    "similarity_threshold": 0.8,
    "institution_filter": "Ticaret Bakanlığı"
  }'
```

## Hata Ayıklama

### Yaygın Sorunlar

1. **401 Unauthorized**: Token eksik veya geçersiz
2. **429 Rate Limited**: Çok fazla istek gönderildi
3. **400 Bad Request**: Query çok kısa (<3 karakter)
4. **500 Internal Error**: AI servis hatası

### Test Komutları

### Sistem Test
```bash
# System health check
python tests/final_vps_ready_test.py

# API connection test
curl -X GET "http://0.0.0.0:5000/health"
```

### Test Sonucu (8 Ağustos 2025) ✅
```bash
# Çalışan örnek
TOKEN="your_access_token_here"
curl -X POST "http://0.0.0.0:5000/api/user/ask" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "KVKK nedir?"}'

# Response: HTTP 200 OK
# Performance: ~3.7s total pipeline
# Confidence: 0.83
# Status: ✅ WORKING
```

## Production Notları

- Rate limiting: 30 req/min per user
- Cache TTL: 1 saat
- Max query length: 1000 karakter
- Max response tokens: 2000
- Timeout: 30 saniye