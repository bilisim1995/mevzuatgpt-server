# Kullanıcı Profil Yönetimi API Endpoint'leri

## 1. GET /api/user/profile

Kullanıcının mevcut profil bilgilerini getirir.

### İstek
```bash
GET /api/user/profile
Authorization: Bearer <token>
```

### Başarılı Yanıt (200)
```json
{
  "id": "user-uuid",
  "email": "kullanici@example.com", 
  "full_name": "Ahmet Yılmaz",
  "ad": "Ahmet",
  "soyad": "Yılmaz", 
  "meslek": "Hukukçu",
  "calistigi_yer": "ABC Hukuk Bürosu",
  "role": "user",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z",
  "current_balance": 45
}
```

## 2. PUT /api/user/profile

Kullanıcının profil bilgilerini günceller.

### İstek
```bash
PUT /api/user/profile
Authorization: Bearer <token>
Content-Type: application/json
```

### İstek Body'si
```json
{
  "full_name": "Ahmet Yılmaz",
  "ad": "Ahmet", 
  "soyad": "Yılmaz",
  "meslek": "Avukat",
  "calistigi_yer": "XYZ Hukuk Bürosu"
}
```

### Güncellenebilir Alanlar
- `full_name`: Tam ad (isteğe bağlı)
- `ad`: Ad (max 50 karakter)
- `soyad`: Soyad (max 50 karakter)  
- `meslek`: Meslek (max 100 karakter)
- `calistigi_yer`: Çalıştığı yer (max 150 karakter)

**NOT:** Tüm alanlar isteğe bağlı. Sadece değiştirmek istediğin alanları gönderebilirsin.

### Başarılı Yanıt (200)
```json
{
  "id": "user-uuid",
  "email": "kullanici@example.com",
  "full_name": "Ahmet Yılmaz", 
  "ad": "Ahmet",
  "soyad": "Yılmaz",
  "meslek": "Avukat",
  "calistigi_yer": "XYZ Hukuk Bürosu",
  "role": "user",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z",
  "current_balance": 45
}
```

## Hata Durumları

### 400 Bad Request
```json
{
  "detail": "Profil güncelleme başarısız"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authorization header missing"
}
```

### 404 Not Found
```json
{
  "detail": "Kullanıcı bulunamadı"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "meslek"],
      "msg": "ensure this value has at most 100 characters", 
      "type": "value_error.any_str.max_length"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Profil güncelleme sırasında hata oluştu"
}
```

## Kullanım Örnekleri

### Sadece Meslek Güncelle
```bash
curl -X PUT "https://your-api.com/api/user/profile" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"meslek": "Senior Hukukçu"}'
```

### Tüm Bilgileri Güncelle
```bash
curl -X PUT "https://your-api.com/api/user/profile" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Dr. Ayşe Demir",
    "ad": "Ayşe", 
    "soyad": "Demir",
    "meslek": "Hukuk Doktoru",
    "calistigi_yer": "İstanbul Üniversitesi Hukuk Fakültesi"
  }'
```

### Profil Bilgilerini Görüntüle
```bash
curl "https://your-api.com/api/user/profile" \
  -H "Authorization: Bearer <token>"
```

## Güvenlik
- JWT token ile kimlik doğrulama gerekli
- Kullanıcı sadece kendi profilini güncelleyebilir
- Email adresi ve şifre bu endpoint'lerle güncellenemez
- Karakter sınırları otomatik kontrol edilir