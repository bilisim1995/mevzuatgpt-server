# Arama Geçmişi API Endpoint'leri

## 1. GET /api/user/search-history

Kullanıcının geçmiş aramalarını sayfalama ve filtreleme ile getirir.

### İstek Parametreleri
```
GET /api/user/search-history?page=1&limit=20&institution=SGK&date_from=2025-08-01&min_reliability=0.8
Authorization: Bearer <token>
```

### Query Parametreleri
- `page`: Sayfa numarası (varsayılan: 1)
- `limit`: Sayfa başına kayıt sayısı (varsayılan: 20, max: 100)
- `institution`: Kurum filtreleme (örn: "SGK", "Çalışma Bakanlığı")
- `date_from`: Başlangıç tarihi (ISO format: "2025-08-01")
- `date_to`: Bitiş tarihi (ISO format: "2025-08-11")
- `min_reliability`: Minimum güvenilirlik skoru (0.0-1.0)
- `search_query`: Önceki sorgular içinde arama

### Başarılı Yanıt (200)
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid-arama-kaydi",
        "query": "Sigortalılık şartları nelerdir?",
        "response": "Sigortalılık için aşağıdaki şartlar gereklidir:\n1. 18 yaş üzerinde olmak\n2. İş sözleşmesi imzalamak\n3. SGK'ya bildirim yapmak...",
        "sources": [
          {
            "document_id": "doc-uuid",
            "title": "SGK Sigortalılık Rehberi",
            "institution": "SGK", 
            "similarity_score": 0.92,
            "pdf_url": "https://cdn.bunny.net/documents/sgk-rehberi.pdf"
          }
        ],
        "reliability_score": 0.87,
        "credits_used": 1,
        "institution_filter": "SGK",
        "results_count": 5,
        "execution_time": 2.45,
        "created_at": "2025-08-10T15:30:25Z"
      },
      {
        "id": "uuid-arama-kaydi-2",
        "query": "Emeklilik yaşı kaçtır?",
        "response": "2025 yılı itibariyle emeklilik yaşı:\n- Kadınlar: 60 yaş\n- Erkekler: 62 yaş\n- Asgari prim gün sayısı: 7200 gün",
        "sources": [
          {
            "document_id": "doc-uuid-2",
            "title": "Emeklilik Mevzuatı",
            "institution": "SGK",
            "similarity_score": 0.95,
            "pdf_url": "https://cdn.bunny.net/documents/emeklilik.pdf"
          }
        ],
        "reliability_score": 0.94,
        "credits_used": 1,
        "institution_filter": "SGK",
        "results_count": 3,
        "execution_time": 1.82,
        "created_at": "2025-08-10T14:15:10Z"
      }
    ],
    "total_count": 47,
    "page": 1,
    "limit": 20,
    "has_more": true
  }
}
```

## 2. GET /api/user/search-history/stats

Kullanıcının arama istatistiklerini getirir.

### İstek
```
GET /api/user/search-history/stats
Authorization: Bearer <token>
```

### Başarılı Yanıt (200)
```json
{
  "success": true,
  "data": {
    "total_searches": 47,
    "total_credits_used": 52,
    "average_reliability": 0.84,
    "most_used_institution": "SGK",
    "searches_this_month": 25,
    "searches_today": 3
  }
}
```

## Özellikler

### Otomatik Kayıt
- Her AI sorgusu otomatik olarak kaydedilir
- Soru, cevap, kaynak belgeler, güvenilirlik skoru saklanır
- Harcanan kredi miktarı ve işlem süresi kaydedilir

### Filtreleme Seçenekleri
- **Kurum**: Sadece belirli kurumların belgelerinde yapılan aramalar
- **Tarih Aralığı**: Belirli tarihler arasındaki aramalar
- **Güvenilirlik**: Minimum güvenilirlik skoru üzerindeki aramalar
- **Metin Arama**: Önceki sorguların içinde arama

### Sayfalama
- Büyük arama geçmişleri için performanslı sayfalama
- Her sayfada maksimum 100 kayıt
- `has_more` ile sonraki sayfaların varlığı bilgisi

### Güvenlik
- Kullanıcı sadece kendi arama geçmişini görebilir
- JWT token ile kimlik doğrulama gerekli
- RLS (Row Level Security) ile veri izolasyonu

## Hata Durumları

### 401 Unauthorized
```json
{
  "detail": "Authorization header missing"
}
```

### 422 Validation Error
```json
{
  "detail": "Validation error: limit must be between 1 and 100"
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "message": "Search history retrieval failed"
}
```