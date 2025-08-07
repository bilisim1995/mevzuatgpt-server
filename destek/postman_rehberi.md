# 📮 Postman ile MevzuatGPT API Kullanımı

Bu rehber, MevzuatGPT API'sini Postman ile nasıl test edeceğini adım adım açıklar.

## 🔗 1. Replit URL'ini Alma

1. **Replit workspace'inde Console tool'u aç**
2. **URL bar'da `.replit.dev` uzantılı URL'i kopyala**
3. **Örnek:** `https://mevzuatgpt--oguzhanboz.replit.dev`

## 🚀 2. Postman Kurulumu

### Base URL Ayarlama
1. **Postman'i aç**
2. **New Collection oluştur: "MevzuatGPT API"**
3. **Environment oluştur:**
   - `base_url`: `https://[your-repl-name]--[username].replit.dev`
   - `token`: `(auth sonrası eklenecek)`

## 🔑 3. Auth İşlemleri

### Kullanıcı Kaydı
```http
POST {{base_url}}/api/auth/register
Content-Type: application/json

{
    "email": "test@example.com",
    "password": "test123456",
    "full_name": "Test Kullanıcı"
}
```

### Giriş Yapma
```http
POST {{base_url}}/api/auth/login
Content-Type: application/json

{
    "email": "test@example.com", 
    "password": "test123456"
}
```

**Cevaptan access_token'i al ve environment'a kaydet!**

## 🔐 4. Authorization Header

Kimlik doğrulama gerektiren endpoint'ler için:

```
Authorization: Bearer {{token}}
```

## 📋 5. Test Senaryoları

### Sistem Durumu
```http
GET {{base_url}}/health
```

### Ana Sayfa
```http
GET {{base_url}}/
```

### API Bilgileri
```http
GET {{base_url}}/api
```

### Admin Endpoints (Admin rolü gerekli)
```http
POST {{base_url}}/api/admin/documents/upload
Authorization: Bearer {{token}}
Content-Type: multipart/form-data
```

### Kullanıcı Endpoints
```http
GET {{base_url}}/api/user/documents
Authorization: Bearer {{token}}
```

```http
POST {{base_url}}/api/user/search
Authorization: Bearer {{token}}
Content-Type: application/json

{
    "query": "anayasa madde",
    "limit": 5
}
```

## ⚠️ 6. Dikkat Edilmesi Gerekenler

1. **CORS:** Replit otomatik CORS ayarları yapar
2. **HTTPS:** Replit her zaman HTTPS kullanır
3. **Rate Limiting:** Aşırı istekten kaçın
4. **Token Expiry:** Token süreleri için auth cevaplarını kontrol et
5. **Environment:** Production vs Development ayarları

## 🐛 7. Hata Ayıklama

### Yaygın Hatalar:
- **404 Not Found:** URL'i ve endpoint'i kontrol et
- **401 Unauthorized:** Token'in doğruluğunu ve süresini kontrol et
- **403 Forbidden:** Kullanıcı rolünü kontrol et
- **422 Validation Error:** İstek body formatını kontrol et
- **500 Internal Error:** Server log'larını kontrol et

### Debug İpuçları:
```http
# Health check ile bağlantıyı test et
GET {{base_url}}/health

# Ana sayfa ile server durumunu kontrol et
GET {{base_url}}/

# API info ile endpoint'leri listele
GET {{base_url}}/api
```

## 📊 8. Collection Export/Import

Postman collection'ını dışa aktarıp paylaşabilirsin:
1. **Collection → Export**
2. **JSON formatında kaydet**
3. **Diğer geliştiricilerle paylaş**

## 🔄 9. Environment Variables

Farklı ortamlar için environment'lar oluştur:

**Development:**
- `base_url`: `http://localhost:5000`

**Replit:**
- `base_url`: `https://[repl-name]--[username].replit.dev`

**Production:** (Deploy sonrası)
- `base_url`: `https://[app-name].replit.app`

---

**💡 İpucu:** Her endpoint için örnek istekleri `endpoints.md` dosyasında bulabilirsin!