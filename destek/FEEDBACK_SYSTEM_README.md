# MevzuatGPT Feedback System - Dökümentasyon

## Genel Bakış
Kullanıcıların AI yanıtlarına olumlu/olumsuz geri bildirim verebileceği modüler feedback sistemi. Mevcut sistemi etkilemeden tamamen ayrı bir modül olarak entegre edilmiştir.

## Özellikler
✅ **Pozitif/Negatif Feedback**: Kullanıcılar 👍/👎 ile değerlendirme yapabilir  
✅ **Spam Koruması**: Aynı kullanıcı aynı sorguya sadece bir feedback verebilir (UPDATE logic)  
✅ **Admin Görünürlük**: Admin'ler tüm feedback'leri görüntüleyebilir  
✅ **Modüler Tasarım**: Mevcut kodu etkilemeden bağımsız modül  
✅ **Backward Compatible**: Eski sistemle tam uyumlu  

## Database Schema

### user_feedback Tablosu
```sql
CREATE TABLE user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    search_log_id UUID NOT NULL,  -- Hangi sorguya feedback verildiği
    query_text TEXT NOT NULL,     -- Orijinal soru
    answer_text TEXT NOT NULL,    -- Verilen cevap
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('positive', 'negative')),
    feedback_comment TEXT,        -- Opsiyonel açıklama
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Spam koruması: Aynı kullanıcı aynı sorguya tek feedback
    UNIQUE(user_id, search_log_id)
);
```

## API Endpoints

### User Endpoints (Kimlik doğrulama gerekli)

#### POST /api/user/feedback/
Feedback gönder veya güncelle
```json
{
    "search_log_id": "uuid-string",
    "feedback_type": "positive|negative",  
    "feedback_comment": "Opsiyonel açıklama"
}
```

#### GET /api/user/feedback/my
Kendi feedback geçmişini görüntüle
```
Query Params:
- page: Sayfa numarası (default: 1)
- limit: Sayfa başına kayıt (default: 20, max: 100)
```

#### GET /api/user/feedback/search/{search_log_id}
Belirli bir sorgu için feedback durumu kontrol et
```json
Response: FeedbackResponse | null
```

#### DELETE /api/user/feedback/{feedback_id}
Kendi feedback'ini sil

### Admin Endpoints (Admin yetkisi gerekli)

#### GET /api/admin/feedback/
Tüm feedback'leri görüntüle
```
Query Params:
- feedback_type: positive|negative (opsiyonel filtre)
- page: Sayfa numarası (default: 1)  
- limit: Sayfa başına kayıt (default: 50, max: 200)
```

#### GET /api/admin/feedback/user/{user_id}
Belirli kullanıcının feedback'lerini görüntüle

#### DELETE /api/admin/feedback/{feedback_id}
Herhangi bir feedback'i sil (admin yetkisi)

## Teknik Mimarı

### Modüler Dosya Yapısı
```
services/feedback_service.py     # Ana iş mantığı
models/feedback_schemas.py       # Pydantic modelleri
api/user/feedback_routes.py      # Kullanıcı endpoint'leri
api/admin/feedback_routes.py     # Admin endpoint'leri
feedback_system_migration.sql   # Database migration
```

### Temel Özellikler

1. **UPSERT Logic**: Aynı kullanıcı + search_log_id için feedback varsa günceller, yoksa yeni ekler
2. **RLS Security**: Supabase Row Level Security ile kullanıcılar sadece kendi feedback'lerini görebilir
3. **Auto Timestamps**: created_at ve updated_at otomatik güncellenir
4. **Type Safety**: Pydantic ile tam type validation
5. **Error Handling**: Kapsamlı hata yönetimi ve logging

## Kullanım Senaryoları

### Frontend Entegrasyonu
```javascript
// AI cevabı altında feedback butonları
<div class="feedback-buttons">
    <button onClick={() => sendFeedback('positive', searchLogId)}>👍</button>
    <button onClick={() => sendFeedback('negative', searchLogId)}>👎</button>
</div>

// Feedback gönderme
async function sendFeedback(type, searchLogId) {
    const response = await fetch('/api/user/feedback/', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            search_log_id: searchLogId,
            feedback_type: type,
            feedback_comment: type === 'negative' ? comment : null
        })
    });
}
```

### Admin Dashboard
```javascript
// Admin feedback listesi
const feedbacks = await fetch('/api/admin/feedback/?feedback_type=negative')
    .then(r => r.json());

// Feedback istatistikleri
const stats = {
    positive: feedbacks.filter(f => f.feedback_type === 'positive').length,
    negative: feedbacks.filter(f => f.feedback_type === 'negative').length
};
```

## Migration Talimatları

### 1. Database Migration
```bash
# Supabase SQL Editor'da feedback_system_migration.sql'i çalıştır
```

### 2. Environment Setup
Zaten mevcut - ek configuration gerekmez

### 3. Test
```bash
# API test
curl -X POST http://localhost:5000/api/user/feedback/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"search_log_id":"test-id","feedback_type":"positive"}'
```

## Güvenlik & Performans

### Güvenlik
- ✅ Supabase RLS politikaları
- ✅ JWT token bazlı authentication
- ✅ User ID validation
- ✅ Input sanitization via Pydantic

### Performans
- ✅ Database indeksler (user_id, search_log_id, feedback_type, created_at)
- ✅ Pagination support
- ✅ Efficient UPSERT operations
- ✅ Connection pooling (FastAPI + Supabase)

### Monitoring
- ✅ Structured logging
- ✅ Error tracking
- ✅ Performance metrics

## Bakım & Geliştirme

### Gelecek Özellikler (İsteğe Bağlı)
- 📊 Feedback analytics dashboard
- 📧 Admin notification system  
- 🔄 Bulk feedback operations
- 📈 AI model performance metrics

### Maintenance
- Eski feedback'leri temizleme (opsiyonel)
- Performans optimizasyonu
- Analytics raporları

---

## ✅ DURUM: PRODUCTION READY
Sistem tamamen operasyonel ve production kullanımına hazır. Modüler tasarım sayesinde mevcut sistemi etkilemeden feedback özelliği aktif.