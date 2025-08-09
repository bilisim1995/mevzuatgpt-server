# MevzuatGPT Feedback System - Postman Test Rehberi

## 🚀 Ön Hazırlık

### 1. Authentication Token Al
```bash
# Login endpoint'i ile token al
POST http://localhost:5000/api/auth/login
Content-Type: application/json

{
    "email": "your-email@example.com",
    "password": "your-password"
}

# Yanıttan access_token'ı kopyala
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {...}
}
```

### 2. Search Log ID Al
```bash
# Önce bir ask sorgusu yap
POST http://localhost:5000/api/user/ask
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
    "query": "Test sorusu",
    "limit": 3
}

# Yanıttan search_log_id'yi not et
{
    "query": "Test sorusu",
    "answer": "...",
    "search_log_id": "uuid-buraya-gelecek"
}
```

## 📋 Feedback Endpoint Testleri

### 1. Feedback Gönder (POST)
```http
POST http://localhost:5000/api/user/feedback/
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
    "search_log_id": "YOUR_SEARCH_LOG_ID",
    "feedback_type": "positive",
    "feedback_comment": "Harika bir cevap!"
}
```

**Beklenen Yanıt:**
```json
{
    "success": true,
    "message": "Feedback başarıyla kaydedildi",
    "feedback": {
        "id": "feedback-uuid",
        "user_id": "user-uuid",
        "search_log_id": "search-log-uuid",
        "feedback_type": "positive",
        "feedback_comment": "Harika bir cevap!",
        "created_at": "2025-08-09T06:30:00.000Z",
        "updated_at": "2025-08-09T06:30:00.000Z"
    }
}
```

### 2. Aynı Feedback'i Güncelle (UPSERT Test)
```http
POST http://localhost:5000/api/user/feedback/
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
    "search_log_id": "SAME_SEARCH_LOG_ID",
    "feedback_type": "negative",
    "feedback_comment": "Aslında cevap yeterli değildi"
}
```

### 3. Kendi Feedback Geçmişini Görüntüle
```http
GET http://localhost:5000/api/user/feedback/my?page=1&limit=10
Authorization: Bearer YOUR_TOKEN
```

**Beklenen Yanıt:**
```json
{
    "feedback_list": [
        {
            "id": "feedback-uuid",
            "feedback_type": "negative",
            "query_text": "Test sorusu",
            "answer_text": "AI cevabı...",
            "feedback_comment": "Aslında cevap yeterli değildi",
            "created_at": "2025-08-09T06:30:00.000Z",
            "updated_at": "2025-08-09T06:32:00.000Z"
        }
    ],
    "total_count": 1,
    "has_more": false,
    "page": 1,
    "limit": 10
}
```

### 4. Belirli Sorgu için Feedback Kontrolü
```http
GET http://localhost:5000/api/user/feedback/search/YOUR_SEARCH_LOG_ID
Authorization: Bearer YOUR_TOKEN
```

### 5. Feedback Sil
```http
DELETE http://localhost:5000/api/user/feedback/YOUR_FEEDBACK_ID
Authorization: Bearer YOUR_TOKEN
```

## 🔧 Admin Endpoint Testleri (Admin Token Gerekli)

### 1. Tüm Feedback'leri Görüntüle
```http
GET http://localhost:5000/api/admin/feedback/?feedback_type=negative&page=1&limit=20
Authorization: Bearer ADMIN_TOKEN
```

### 2. Belirli Kullanıcının Feedback'leri
```http
GET http://localhost:5000/api/admin/feedback/user/USER_UUID?page=1&limit=20
Authorization: Bearer ADMIN_TOKEN
```

### 3. Herhangi Bir Feedback'i Sil (Admin)
```http
DELETE http://localhost:5000/api/admin/feedback/FEEDBACK_ID
Authorization: Bearer ADMIN_TOKEN
```

## 📊 Test Senaryoları

### Senaryo 1: Tam Feedback Döngüsü
1. Login yap → Token al
2. Ask sorgusu yap → search_log_id al
3. Positive feedback gönder
4. Aynı search_log_id ile negative feedback gönder (güncelleme testi)
5. Feedback geçmişini kontrol et
6. Feedback'i sil

### Senaryo 2: Spam Koruması Testi
1. Aynı search_log_id ile birden fazla feedback gönder
2. Her seferinde önceki feedback'in güncellenmesini kontrol et
3. Yeni kayıt eklenmediğini doğrula

### Senaryo 3: Admin Yetki Testi
1. Normal kullanıcı token'ı ile admin endpoint'e istek at
2. 403 Forbidden almalısın
3. Admin token'ı ile aynı endpoint'i test et

## ⚠️ Hata Senaryoları

### 1. Geçersiz Token
```http
POST http://localhost:5000/api/user/feedback/
Authorization: Bearer invalid-token

# Beklenen: 401 Unauthorized
```

### 2. Geçersiz search_log_id
```http
POST http://localhost:5000/api/user/feedback/
Authorization: Bearer YOUR_TOKEN

{
    "search_log_id": "non-existent-uuid",
    "feedback_type": "positive"
}

# Beklenen: 404 Not Found
```

### 3. Geçersiz feedback_type
```http
POST http://localhost:5000/api/user/feedback/
Authorization: Bearer YOUR_TOKEN

{
    "search_log_id": "YOUR_SEARCH_LOG_ID",
    "feedback_type": "invalid-type"
}

# Beklenen: 422 Validation Error
```

## 🔍 Postman Collection Setup

### Environment Variables
```
base_url = http://localhost:5000
token = {{YOUR_ACCESS_TOKEN}}
search_log_id = {{YOUR_SEARCH_LOG_ID}}
```

### Pre-request Script (Token otomatik ekleme)
```javascript
pm.request.headers.add({
    key: 'Authorization',
    value: 'Bearer ' + pm.environment.get('token')
});
```

### Test Scripts
```javascript
// Response status kontrolü
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

// JSON response kontrolü
pm.test("Response is JSON", function () {
    pm.response.to.be.json;
});

// Success field kontrolü
pm.test("Success is true", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData.success).to.eql(true);
});
```

---

## 🎯 Hızlı Test Adımları

1. **Login** → Token kopyala
2. **Ask sorgusu** → search_log_id kopyala  
3. **Feedback gönder** → Başarılı response kontrol
4. **Feedback güncelle** → UPSERT test
5. **Geçmiş görüntüle** → Pagination test
6. **Admin testleri** → Yetki kontrolü

Bu rehber ile feedback sisteminin tüm özelliklerini test edebilirsiniz!