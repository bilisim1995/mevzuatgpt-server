# 📋 MevzuatGPT Kullanıcı API Endpoint'leri

Bu dokümanda kullanıcıların profil ve kredi bilgileri için kullanabileceği tüm API endpoint'leri açıklanmaktadır.

## 🔗 Base URL
```
http://localhost:5000
```

## 🔑 Yetkilendirme
Tüm endpoint'ler JWT token gerektirir:
```
Authorization: Bearer {access_token}
```
Token `/api/auth/login` endpoint'inden alınır.

---

## 💰 KREDİ YÖNETİMİ ENDPOINT'LERİ

### 1. Kredi Bakiyesi Sorgulama
```http
GET /api/user/credits
```

**Açıklama:** Kullanıcının mevcut kredi bakiyesini ve admin durumunu getirir.

**Request Headers:**
```
Authorization: Bearer {token}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "current_balance": 58,
    "is_admin": true,
    "unlimited": true
  }
}
```

**Response Alanları:**
- `current_balance`: Mevcut kredi bakiyesi
- `is_admin`: Kullanıcının admin olup olmadığı
- `unlimited`: Admin kullanıcılar için true

---

### 2. Kredi İşlem Geçmişi
```http
GET /api/user/credits/history?limit=20
```

**Açıklama:** Kullanıcının kredi transaction geçmişini listeler.

**Query Parametreleri:**
- `limit` (opsiyonel): Maksimum kayıt sayısı (varsayılan: 20, maksimum: 100)

**Response:**
```json
{
  "success": true,
  "data": {
    "transactions": [
      {
        "id": "uuid-string",
        "type": "addition",
        "amount": 30,
        "balance_after": 58,
        "description": "Başlangıç kredisi",
        "date": "2025-08-09T22:00:00.000Z",
        "query_id": null
      },
      {
        "id": "uuid-string",
        "type": "deduction",
        "amount": -2,
        "balance_after": 56,
        "description": "Sorgu kredisi",
        "date": "2025-08-09T22:05:00.000Z",
        "query_id": "query-uuid"
      }
    ],
    "total_count": 2
  }
}
```

**Transaction Türleri:**
- `addition`: Kredi ekleme
- `deduction`: Kredi düşme

---

### 3. Detaylı Kredi Özet Raporu
```http
GET /api/user/credits/summary
```

**Açıklama:** Kullanıcının kredi durumu hakkında detaylı özet bilgileri.

**Response:**
```json
{
  "success": true,
  "data": {
    "current_balance": 58,
    "total_earned": 58,
    "total_spent": 0,
    "recent_transactions": [...],
    "is_admin": true
  }
}
```

**Response Alanları:**
- `current_balance`: Mevcut bakiye
- `total_earned`: Toplam kazanılan kredi
- `total_spent`: Toplam harcanan kredi
- `recent_transactions`: Son 5 işlem
- `is_admin`: Admin durumu

---

## 💬 FEEDBACK YÖNETİMİ ENDPOINT'LERİ

### 3. Feedback Gönderme
```http
POST /api/user/feedback/
```

**Açıklama:** AI cevabına kullanıcı geri bildirimi gönderir.

**Request Body:**
```json
{
  "search_log_id": "50618ab0-12b0-4393-8666-f99530d0c785",
  "feedback_type": "positive",
  "feedback_comment": "Çok yararlı bilgi, teşekkürler!"
}
```

**Request Alanları:**
- `search_log_id`: Sorgu yanıtından alınan UUID (zorunlu)
- `feedback_type`: "positive", "negative", "neutral" (zorunlu)
- `feedback_comment`: Ek yorum (opsiyonel, max 1000 karakter)

**Response:**
```json
{
  "success": true,
  "message": "Feedback başarıyla kaydedildi",
  "feedback": {
    "id": "0a23c78d-cd9c-4e3d-b4a3-fb5a271b1838",
    "user_id": "2338e165-8b57-4ef6-aec7-bef61ace8e6b",
    "search_log_id": "50618ab0-12b0-4393-8666-f99530d0c785",
    "query_text": "Sigortalılık şartları",
    "answer_text": "AI yanıtı metni...",
    "feedback_type": "positive",
    "feedback_comment": "Çok yararlı bilgi, teşekkürler!",
    "created_at": "2025-08-10T08:12:38.266694Z",
    "updated_at": "2025-08-10T08:12:38.266694Z"
  }
}
```

---

### 4. Feedback Geçmişi Görüntüleme
```http
GET /api/user/feedback/my?page=1&limit=10
```

**Açıklama:** Kullanıcının tüm feedback geçmişini sayfalı şekilde getirir.

**Query Parametreleri:**
- `page`: Sayfa numarası (varsayılan: 1)
- `limit`: Sayfa başına kayıt (varsayılan: 10, max: 100)

**Response:**
```json
{
  "success": true,
  "message": "Feedback geçmişi başarıyla getirildi",
  "data": {
    "feedbacks": [
      {
        "id": "0a23c78d-cd9c-4e3d-b4a3-fb5a271b1838",
        "search_log_id": "50618ab0-12b0-4393-8666-f99530d0c785",
        "query_text": "Sigortalılık şartları nelerdir?",
        "answer_text": "Sigortalılık için gerekli şartlar şunlardır: 1) İş akdi...",
        "feedback_type": "positive",
        "feedback_comment": "Çok yararlı bilgi, teşekkürler!",
        "created_at": "2025-08-10T08:12:38.266694Z",
        "updated_at": "2025-08-10T08:12:38.266694Z"
      },
      {
        "id": "1b34d89e-de0d-5e4e-c5b4-gc6a382c2949",
        "search_log_id": "61729bc1-23c1-5404-9777-a00631e1d896",
        "query_text": "İş sözleşmesi nasıl feshedilir?",
        "answer_text": "İş sözleşmesi feshi için uyulması gereken prosedürler...",
        "feedback_type": "negative", 
        "feedback_comment": "Bilgiler eksik, daha detaylı olmalı",
        "created_at": "2025-08-09T15:30:22.123456Z",
        "updated_at": "2025-08-09T15:30:22.123456Z"
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 5,
      "total_items": 47,
      "items_per_page": 10,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

---

### 5. Belirli Sorgu Feedback'i Görüntüleme
```http
GET /api/user/feedback/search/{search_log_id}
```

**Açıklama:** Belirli bir sorguya verilen feedback'i getirir.

**Path Parametresi:**
- `search_log_id`: Sorgu UUID'si

**Response:**
```json
{
  "success": true,
  "message": "Feedback başarıyla getirildi",
  "data": {
    "feedback": {
      "id": "0a23c78d-cd9c-4e3d-b4a3-fb5a271b1838",
      "search_log_id": "50618ab0-12b0-4393-8666-f99530d0c785",
      "query_text": "Sigortalılık şartları nelerdir?",
      "answer_text": "Sigortalılık için gerekli şartlar...",
      "feedback_type": "positive",
      "feedback_comment": "Çok yararlı bilgi!",
      "created_at": "2025-08-10T08:12:38.266694Z"
    }
  }
}
```

**Feedback yoksa:**
```json
{
  "success": true,
  "message": "Bu sorgu için feedback bulunamadı",
  "data": {
    "feedback": null
  }
}
```

---

## 👤 PROFİL YÖNETİMİ ENDPOINT'LERİ

### 4. Temel Kullanıcı Bilgileri
```http
GET /api/auth/me
```

**Açıklama:** Mevcut kullanıcının temel profil bilgilerini getirir.

**Response:**
```json
{
  "id": "0dea4151-9ab9-453e-8ef9-2bb94649cc16",
  "email": "user@example.com",
  "full_name": "Ad Soyad",
  "ad": "Ad",
  "soyad": "Soyad",
  "meslek": "Avukat",
  "calistigi_yer": "Hukuk Bürosu",
  "role": "user",
  "created_at": "2025-08-09T22:00:00.000Z"
}
```

---

### 5. Detaylı Profil Bilgileri
```http
GET /api/user/profile
```

**Açıklama:** Kullanıcının tam profil bilgilerini getirir (auth/me ile aynı formatta).

**Response:** Yukarıdaki ile aynı format.

---

### 6. Profil Güncelleme
```http
PUT /api/user/profile
```

**Açıklama:** Kullanıcının profil bilgilerini günceller.

**Request Body:**
```json
{
  "full_name": "Yeni Ad Soyad",
  "ad": "Yeni Ad",
  "soyad": "Yeni Soyad",
  "meslek": "Hukukçu",
  "calistigi_yer": "Yeni Şirket"
}
```

**Güncellenebilir Alanlar:**
- `full_name`: Tam ad
- `ad`: Ad
- `soyad`: Soyad
- `meslek`: Meslek
- `calistigi_yer`: Çalıştığı yer

**Response:** Güncellenmiş kullanıcı bilgileri (GET formatında).

---

### 7. Token Doğrulama
```http
GET /api/auth/verify-token
```

**Açıklama:** Mevcut token'ın geçerli olup olmadığını kontrol eder.

**Response:** Token geçerliyse kullanıcı bilgileri, değilse 401 hatası.

---

### 8. Çıkış Yapma
```http
POST /api/auth/logout
```

**Açıklama:** Kullanıcı oturumunu sonlandırır.

**Response:**
```json
{
  "message": "Başarıyla çıkış yapıldı",
  "detail": "Token'ı client tarafında kaldırın"
}
```

---

## 💻 KULLANIM ÖRNEKLERİ

### JavaScript/Fetch
```javascript
// Token'ı localStorage'dan al
const token = localStorage.getItem('access_token');

// Kredi bakiyesi kontrolü
async function getCredits() {
  const response = await fetch('/api/user/credits', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const data = await response.json();
  if (data.success) {
    console.log('Kredi Bakiyesi:', data.data.current_balance);
    console.log('Admin mi:', data.data.is_admin);
  }
}

// Profil güncelleme
async function updateProfile() {
  const response = await fetch('/api/user/profile', {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      ad: "Yeni Ad",
      soyad: "Yeni Soyad",
      meslek: "Hukukçu"
    })
  });
  
  const data = await response.json();
  console.log('Profil güncellendi:', data);
}
```

### cURL Örnekleri
```bash
# Token değişkeni
TOKEN="your-jwt-token-here"

# Kredi bakiyesi sorgulama
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:5000/api/user/credits

# Kredi geçmişi (son 10 kayıt)
curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:5000/api/user/credits/history?limit=10"

# Profil bilgilerini alma
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:5000/api/user/profile

# Profil güncelleme
curl -X PUT \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"ad":"Yeni Ad","meslek":"Avukat","calistigi_yer":"Hukuk Bürosu"}' \
     http://localhost:5000/api/user/profile

# Token doğrulama
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:5000/api/auth/verify-token
```

### Python Requests
```python
import requests

# Token
token = "your-jwt-token"
headers = {"Authorization": f"Bearer {token}"}

# Kredi bakiyesi
response = requests.get("http://localhost:5000/api/user/credits", headers=headers)
credits = response.json()
print(f"Kredi: {credits['data']['current_balance']}")

# Profil güncelleme
profile_data = {
    "ad": "Yeni Ad",
    "soyad": "Yeni Soyad",
    "meslek": "Hukukçu"
}
response = requests.put(
    "http://localhost:5000/api/user/profile", 
    headers={**headers, "Content-Type": "application/json"},
    json=profile_data
)
```

---

## ⚠️ HATA KODLARI

| HTTP Kodu | Açıklama |
|-----------|----------|
| 200 | Başarılı |
| 401 | Geçersiz veya eksik token |
| 403 | Yetkisiz erişim |
| 404 | Endpoint bulunamadı |
| 422 | Geçersiz veri formatı |
| 500 | Sunucu hatası |

## 🔐 GÜVENLİK NOTLARI

1. **Token Güvenliği**: JWT token'ları güvenli şekilde saklayın
2. **HTTPS**: Production ortamında mutlaka HTTPS kullanın
3. **Token Süresi**: Token'lar 1 saat geçerlidir
4. **Rate Limiting**: Aşırı istek göndermeyin
5. **Data Validation**: Gönderdiğiniz verileri doğrulayın

---

## 🆘 DESTEK

Teknik destek için:
- GitHub Issues
- Email: admin@mevzuatgpt.com
- API Dokümantasyonu: `/docs` endpoint'i

**Son Güncelleme:** 9 Ağustos 2025