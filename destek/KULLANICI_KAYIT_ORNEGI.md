# MevzuatGPT - Genişletilmiş Kullanıcı Kayıt Sistemi

## 🎯 Özellikler

Kullanıcı kayıt sistemi artık şu opsiyonel bilgileri desteklemektedir:

- **Ad**: Kullanıcının adı (max 50 karakter)
- **Soyad**: Kullanıcının soyadı (max 50 karakter)  
- **Meslek**: Kullanıcının mesleği (max 100 karakter)
- **Çalıştığı Yer**: Kurumu/şirketi (max 150 karakter)

**Not:** Tüm bu alanlar opsiyoneldir ve boş bırakılabilir.

## 🔧 API Endpoint'leri

### 1. Genişletilmiş Kullanıcı Kaydı

```http
POST /api/auth/register
Content-Type: application/json
```

**Request Body:**
```json
{
    "email": "ahmet.yilmaz@example.com",
    "password": "SecurePass123",
    "confirm_password": "SecurePass123",
    "full_name": "Ahmet Yılmaz",
    "ad": "Ahmet",
    "soyad": "Yılmaz", 
    "meslek": "Avukat",
    "calistigi_yer": "İstanbul Adalet Sarayı"
}
```

**Minimal Request (sadece gerekli alanlar):**
```json
{
    "email": "user@example.com",
    "password": "SecurePass123",
    "confirm_password": "SecurePass123"
}
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
        "id": "12345678-1234-1234-1234-123456789abc",
        "email": "ahmet.yilmaz@example.com",
        "full_name": "Ahmet Yılmaz",
        "ad": "Ahmet",
        "soyad": "Yılmaz",
        "meslek": "Avukat",
        "calistigi_yer": "İstanbul Adalet Sarayı",
        "role": "user",
        "created_at": "2025-08-09T12:30:00Z"
    }
}
```

### 2. Kullanıcı Profil Görüntüleme

```http
GET /api/user/profile
Authorization: Bearer <token>
```

**Response:**
```json
{
    "id": "12345678-1234-1234-1234-123456789abc",
    "email": "ahmet.yilmaz@example.com",
    "full_name": "Ahmet Yılmaz",
    "ad": "Ahmet",
    "soyad": "Yılmaz",
    "meslek": "Avukat",
    "calistigi_yer": "İstanbul Adalet Sarayı",
    "role": "user",
    "created_at": "2025-08-09T12:30:00Z"
}
```

### 3. Profil Güncelleme

```http
PUT /api/user/profile
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body (tüm alanlar opsiyonel):**
```json
{
    "full_name": "Ahmet Yılmaz",
    "ad": "Ahmet",
    "soyad": "Yılmaz", 
    "meslek": "Kıdemli Avukat",
    "calistigi_yer": "Yılmaz Hukuk Bürosu"
}
```

**Kısmi güncelleme örneği:**
```json
{
    "meslek": "Başkonsolos",
    "calistigi_yer": "T.C. İstanbul Başkonsolosluğu"
}
```

## 📊 Supabase Veritabanı Yapısı

### Migration Gereksinimleri

`destek/user_profile_migration.sql` dosyasını Supabase SQL Editor'da çalıştırın:

```sql
-- user_profiles tablosuna yeni kolonlar ekle
ALTER TABLE public.user_profiles 
ADD COLUMN IF NOT EXISTS ad VARCHAR(50),
ADD COLUMN IF NOT EXISTS soyad VARCHAR(50), 
ADD COLUMN IF NOT EXISTS meslek VARCHAR(100),
ADD COLUMN IF NOT EXISTS calistigi_yer VARCHAR(150);
```

### Tablo Yapısı (Güncellenmiş)

| Alan | Tip | Açıklama |
|------|-----|----------|
| id | UUID | Birincil anahtar |
| email | VARCHAR | Email adresi (zorunlu) |
| full_name | VARCHAR | Tam isim (opsiyonel) |
| **ad** | VARCHAR(50) | Ad (opsiyonel) |
| **soyad** | VARCHAR(50) | Soyad (opsiyonel) |
| **meslek** | VARCHAR(100) | Meslek (opsiyonel) |
| **calistigi_yer** | VARCHAR(150) | Çalıştığı yer (opsiyonel) |
| role | VARCHAR | Kullanıcı rolü (user/admin) |
| created_at | TIMESTAMP | Oluşturulma tarihi |
| updated_at | TIMESTAMP | Son güncelleme |

## 🔍 Arama ve Filtreleme

Performans için indeksler oluşturuldu:

```sql
-- Arama performansı için indeksler
CREATE INDEX idx_user_profiles_ad ON public.user_profiles(ad);
CREATE INDEX idx_user_profiles_soyad ON public.user_profiles(soyad);  
CREATE INDEX idx_user_profiles_meslek ON public.user_profiles(meslek);
CREATE INDEX idx_user_profiles_calistigi_yer ON public.user_profiles(calistigi_yer);

-- Tam isim arama için composite index
CREATE INDEX idx_user_profiles_full_name_components 
ON public.user_profiles(ad, soyad);
```

## 🛡️ Güvenlik

- Tüm yeni alanlar opsiyoneldir
- Maksimum karakter sınırları belirlenmiştir
- Supabase RLS (Row Level Security) politikaları geçerlidir
- JWT token tabanlı kimlik doğrulama

## 📋 Validasyon Kuralları

### Frontend Validasyon Önerileri

```javascript
// React/Vue.js için örnek validasyon
const profileValidation = {
    ad: {
        maxLength: 50,
        pattern: /^[a-zA-ZğüşıöçĞÜŞİÖÇ\s]*$/,
        message: "Ad sadece harf ve boşluk içerebilir"
    },
    soyad: {
        maxLength: 50,
        pattern: /^[a-zA-ZğüşıöçĞÜŞİÖÇ\s]*$/,
        message: "Soyad sadece harf ve boşluk içerebilir"
    },
    meslek: {
        maxLength: 100,
        message: "Meslek en fazla 100 karakter olabilir"
    },
    calistigi_yer: {
        maxLength: 150,
        message: "Çalışılan yer en fazla 150 karakter olabilir"
    }
};
```

## 📱 Frontend Entegrasyonu

### Kayıt Formu Örneği

```html
<form class="registration-form">
    <div class="required-fields">
        <input type="email" name="email" placeholder="Email *" required>
        <input type="password" name="password" placeholder="Şifre *" required>
        <input type="password" name="confirm_password" placeholder="Şifre Tekrar *" required>
    </div>
    
    <div class="optional-fields">
        <h3>Opsiyonel Bilgiler</h3>
        <input type="text" name="ad" placeholder="Ad" maxlength="50">
        <input type="text" name="soyad" placeholder="Soyad" maxlength="50">
        <input type="text" name="meslek" placeholder="Meslek" maxlength="100">
        <input type="text" name="calistigi_yer" placeholder="Çalıştığı Yer" maxlength="150">
    </div>
    
    <button type="submit">Kayıt Ol</button>
</form>
```

## 🧪 Test Örnekleri

### Postman Test Collection

```json
{
    "name": "Extended User Registration",
    "requests": [
        {
            "name": "Register with Full Profile",
            "method": "POST",
            "url": "{{base_url}}/api/auth/register",
            "body": {
                "email": "test.user@example.com",
                "password": "TestPass123",
                "confirm_password": "TestPass123",
                "ad": "Test",
                "soyad": "User",
                "meslek": "Test Engineer",
                "calistigi_yer": "Tech Company"
            }
        },
        {
            "name": "Register Minimal",
            "method": "POST",
            "url": "{{base_url}}/api/auth/register",
            "body": {
                "email": "minimal@example.com",
                "password": "TestPass123", 
                "confirm_password": "TestPass123"
            }
        },
        {
            "name": "Update Profile",
            "method": "PUT",
            "url": "{{base_url}}/api/user/profile",
            "headers": {
                "Authorization": "Bearer {{user_token}}"
            },
            "body": {
                "meslek": "Senior Software Engineer",
                "calistigi_yer": "International Tech Corp"
            }
        }
    ]
}
```

## 📈 İstatistikler ve Raporlama

Admin kullanıcıları için profil tamamlama oranları:

```sql
-- Profil tamamlama istatistikleri
SELECT 
    COUNT(*) as total_users,
    COUNT(ad) as users_with_name,
    COUNT(meslek) as users_with_profession,
    COUNT(calistigi_yer) as users_with_workplace,
    ROUND(COUNT(ad) * 100.0 / COUNT(*), 2) as name_completion_rate,
    ROUND(COUNT(meslek) * 100.0 / COUNT(*), 2) as profession_completion_rate
FROM public.user_profiles;
```

## 🚀 Deployment Notları

1. **Migration çalıştırın:** `destek/user_profile_migration.sql`
2. **API server'ı yeniden başlatın**
3. **Frontend formlarını güncelleyin**
4. **Test senaryolarını çalıştırın**

Sistem artık genişletilmiş kullanıcı profilleri ile tam operasyonel!