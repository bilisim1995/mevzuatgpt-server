# MevzuatGPT Destek Sistemi API Endpoint'leri

## 📋 Genel Bilgiler

Base URL: `http://localhost:5000` (Geliştirme)
Tüm istekler JWT Bearer token gerektirir.

## 🔑 Yetkilendirme

```http
Authorization: Bearer <jwt_token>
```

## 👤 Kullanıcı Endpoint'leri

### 1. Yeni Ticket Oluştur
```http
POST /api/user/support/tickets
Content-Type: application/json
```

**Request Body:**
```json
{
    "subject": "PDF yükleme sorunu",
    "category": "teknik_sorun",
    "priority": "orta",
    "message": "Detaylı sorun açıklaması..."
}
```

**Response:**
```json
{
    "success": true,
    "message": "Destek talebiniz başarıyla oluşturuldu",
    "ticket": {
        "id": "uuid",
        "ticket_number": "TK-000001",
        "subject": "PDF yükleme sorunu",
        "category": "teknik_sorun",
        "priority": "orta",
        "status": "acik",
        "created_at": "2025-08-09T06:30:00Z"
    }
}
```

### 2. Kendi Ticket'larını Listele
```http
GET /api/user/support/tickets?page=1&limit=10&status=acik&category=teknik_sorun
```

**Query Parameters:**
- `page`: Sayfa numarası (varsayılan: 1)
- `limit`: Sayfa başına kayıt (varsayılan: 10, max: 50)
- `status`: acik, cevaplandi, kapatildi
- `category`: teknik_sorun, hesap_sorunu, vb.
- `priority`: dusuk, orta, yuksek, acil
- `search`: Konu içinde arama

**Response:**
```json
{
    "tickets": [
        {
            "id": "uuid",
            "ticket_number": "TK-000001",
            "subject": "PDF yükleme sorunu",
            "category": "teknik_sorun",
            "priority": "orta",
            "status": "acik",
            "message_count": 2,
            "last_reply_at": "2025-08-09T06:45:00Z",
            "created_at": "2025-08-09T06:30:00Z"
        }
    ],
    "total_count": 5,
    "has_more": false,
    "page": 1,
    "limit": 10
}
```

### 3. Ticket Detayı ve Mesajları
```http
GET /api/user/support/tickets/{ticket_id}
```

**Response:**
```json
{
    "id": "uuid",
    "ticket_number": "TK-000001",
    "subject": "PDF yükleme sorunu",
    "category": "teknik_sorun",
    "priority": "orta",
    "status": "cevaplandi",
    "message_count": 3,
    "messages": [
        {
            "id": "uuid",
            "sender_id": "user_uuid",
            "sender_name": "Ahmet Yılmaz",
            "sender_email": "ahmet@example.com",
            "is_admin": false,
            "message": "İlk mesaj içeriği...",
            "created_at": "2025-08-09T06:30:00Z"
        },
        {
            "id": "uuid",
            "sender_id": "admin_uuid",
            "sender_name": "Destek Ekibi",
            "sender_email": "support@example.com",
            "is_admin": true,
            "message": "Admin yanıtı...",
            "created_at": "2025-08-09T06:45:00Z"
        }
    ],
    "created_at": "2025-08-09T06:30:00Z",
    "updated_at": "2025-08-09T06:45:00Z"
}
```

### 4. Ticket'a Mesaj Gönder
```http
POST /api/user/support/tickets/{ticket_id}/reply
Content-Type: application/json
```

**Request Body:**
```json
{
    "message": "Ek bilgi veya yanıt mesajı..."
}
```

**Response:**
```json
{
    "success": true,
    "message": "Mesajınız başarıyla gönderildi",
    "support_message": {
        "id": "uuid",
        "ticket_id": "ticket_uuid",
        "sender_id": "user_uuid",
        "message": "Ek bilgi veya yanıt mesajı...",
        "created_at": "2025-08-09T07:00:00Z"
    }
}
```

### 5. Sadece Mesajları Getir
```http
GET /api/user/support/tickets/{ticket_id}/messages
```

## 👑 Admin Endpoint'leri

### 1. Tüm Ticket'ları Listele (Admin)
```http
GET /api/admin/support/tickets?page=1&limit=20&status=acik&search=PDF
```

**Query Parameters:**
- Kullanıcı parametreleri + `user_id`: Belirli kullanıcı filtresi

**Response:** (Kullanıcı bilgileri dahil genişletilmiş format)

### 2. Herhangi Bir Ticket Detayı (Admin)
```http
GET /api/admin/support/tickets/{ticket_id}
```

### 3. Admin Yanıtı Gönder
```http
POST /api/admin/support/tickets/{ticket_id}/reply
Content-Type: application/json
```

**Request Body:**
```json
{
    "message": "Admin yanıtı ve çözüm önerisi..."
}
```

**Not:** Admin yanıtı ticket durumunu otomatik olarak "cevaplandi" yapar.

### 4. Ticket Durumu Güncelle
```http
PUT /api/admin/support/tickets/{ticket_id}/status
Content-Type: application/json
```

**Request Body:**
```json
{
    "status": "kapatildi"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Ticket durumu kapatildi olarak güncellendi"
}
```

### 5. Ticket İstatistikleri
```http
GET /api/admin/support/tickets/stats
```

**Response:**
```json
{
    "total_tickets": 150,
    "open_tickets": 25,
    "answered_tickets": 45,
    "closed_tickets": 80,
    "by_category": {
        "teknik_sorun": 60,
        "hesap_sorunu": 30,
        "ozellik_talebi": 25,
        "guvenlik": 5,
        "faturalandirma": 15,
        "genel_soru": 10,
        "diger": 5
    },
    "by_priority": {
        "dusuk": 80,
        "orta": 50,
        "yuksek": 15,
        "acil": 5
    }
}
```

### 6. Kullanıcının Ticket'ları (Admin)
```http
GET /api/admin/support/tickets/user/{user_id}?status=acik
```

### 7. Ticket Sil (Admin - Dikkatli!)
```http
DELETE /api/admin/support/tickets/{ticket_id}
```

**Response:**
```json
{
    "success": true,
    "message": "Ticket TK-000001 başarıyla silindi"
}
```

## 📊 Kategoriler ve Öncelikler

### Kategoriler
- `teknik_sorun`: PDF yükleme, sistem hataları, performans
- `hesap_sorunu`: Login, kredi, profil ayarları  
- `ozellik_talebi`: Yeni özellik istekleri
- `guvenlik`: Güvenlik endişeleri, şüpheli aktiviteler
- `faturalandirma`: Ödeme sorunları, fatura soruları
- `genel_soru`: Genel kullanım soruları, rehberlik
- `diger`: Diğer konular

### Öncelikler
- `dusuk`: Genel sorular, özellik talepleri
- `orta`: Standart teknik sorunlar (varsayılan)
- `yuksek`: Kritik işlevsellik sorunları
- `acil`: Güvenlik sorunları, sistem erişim sorunları

### Durumlar
- `acik`: Yeni veya kullanıcı yanıtı bekleyen
- `cevaplandi`: Admin tarafından yanıtlanmış
- `kapatildi`: Çözüme ulaşmış veya kapatılmış

## ❌ Hata Kodları

### 400 - Bad Request
```json
{
    "success": false,
    "error": "Validation hatası veya iş kuralı ihlali"
}
```

### 401 - Unauthorized
```json
{
    "success": false,
    "error": "Authorization header missing veya invalid token"
}
```

### 403 - Forbidden
```json
{
    "success": false,
    "error": "Bu işlem için admin yetkisi gerekli"
}
```

### 404 - Not Found
```json
{
    "success": false,
    "error": "Ticket bulunamadı veya erişim yetkiniz yok"
}
```

### 422 - Validation Error
```json
{
    "detail": [
        {
            "loc": ["body", "subject"],
            "msg": "ensure this value has at least 5 characters",
            "type": "value_error.any_str.min_length"
        }
    ]
}
```

## 🧪 Test Etme

1. **Postman Collection:** `Destek-System.postman_collection.json` dosyasını Postman'e import edin
2. **Environment Variables:** `base_url`, `user_token`, `admin_token` değerlerini ayarlayın
3. **Test Flow:** Authentication → User Operations → Admin Operations → Error Handling

## 🔒 Güvenlik

- Tüm endpoint'ler JWT token gerektirir
- RLS politikaları ile kullanıcı izolasyonu
- Admin yetki kontrolü her admin endpoint'te
- Input validation ve sanitization
- Rate limiting (Redis tabanlı)

## 📈 Performans

- PostgreSQL indeksleri ile optimize edilmiş sorgular
- Pagination ile büyük veri setleri desteği
- Async/await ile yüksek concurrency
- Redis caching ile hızlı yanıt süreleri