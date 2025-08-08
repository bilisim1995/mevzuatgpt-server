# 💳 Kredi Sistemi Kullanım Rehberi

MevzuatGPT'de kullanıcıların sistemdeki sorgu kullanımlarını yönetmek için kredi sistemi entegre edilmiştir. Bu rehber, kredi sisteminin nasıl çalıştığını ve nasıl yönetileceğini açıklar.

## 📋 Sistem Genel Bakış

### Kredi Hesaplama Formülü
```
Toplam Kredi = Temel Kredi (1) + Karakter Kredisi (uzunluk ÷ 100)
```

**Örnekler:**
- 50 karakter sorgu = 1 kredi (temel)
- 150 karakter sorgu = 2 kredi (1 temel + 1 karakter)
- 350 karakter sorgu = 4 kredi (1 temel + 3 karakter)

### Kullanıcı Tipleri
- **Normal Kullanıcı**: 30 başlangıç kredisi, kredi kontrolü aktif
- **Admin Kullanıcı**: Unlimited kredi, kontrol bypass

## 🔧 API Endpoints

### Kullanıcı Kredi Endpoints

#### GET `/api/user/credits/balance`
Mevcut kredi bakiyesini görüntüle

**Response:**
```json
{
  "success": true,
  "data": {
    "current_balance": 25,
    "is_admin": false,
    "unlimited": false
  }
}
```

#### GET `/api/user/credits/history?limit=20`
Kredi transaction geçmişini görüntüle

**Response:**
```json
{
  "success": true,
  "data": {
    "transactions": [
      {
        "id": "uuid",
        "type": "deduction",
        "amount": -2,
        "balance_after": 25,
        "description": "Sorgu: 'sigortalılık şartları nelerdir?'",
        "date": "2025-08-08T20:30:00Z",
        "query_id": null
      }
    ],
    "total_count": 15
  }
}
```

#### GET `/api/user/credits/summary`
Detaylı kredi özeti

**Response:**
```json
{
  "success": true,
  "data": {
    "current_balance": 25,
    "total_earned": 30,
    "total_spent": 5,
    "recent_transactions": [...],
    "is_admin": false
  }
}
```

### Admin Kredi Endpoints

#### POST `/api/admin/credits/add`
Kullanıcıya kredi ekle (sadece admin)

**Request:**
```json
{
  "user_id": "user-uuid",
  "amount": 50,
  "description": "Bonus kredi"
}
```

#### POST `/api/admin/credits/set`
Kullanıcının kredi bakiyesini belirli değere ayarla

**Request:**
```json
{
  "user_id": "user-uuid", 
  "amount": 100,
  "description": "Bakiye güncelleme"
}
```

#### GET `/api/admin/credits/users?page=1&limit=20`
Tüm kullanıcıların kredi durumunu listele

#### GET `/api/admin/credits/user/{user_id}/history`
Belirli kullanıcının kredi geçmişini görüntüle

## 💬 Ask Endpoint Entegrasyonu

### Kredi Kontrolü Süreci

1. **Kredi Hesaplama**: Sorgu uzunluğuna göre gerekli kredi hesaplanır
2. **Bakiye Kontrolü**: Kullanıcının yeterli kredisi var mı kontrol edilir
3. **Kredi Düşümü**: İşlem başlamadan önce kredi düşülür
4. **İşlem Tamamlama**: Normal ask pipeline çalışır
5. **Hata Durumunda İade**: İşlem başarısız olursa kredi otomatik iade edilir

### POST `/api/user/ask` Response Örneği

**Başarılı Response:**
```json
{
  "success": true,
  "data": {
    "query": "sigortalılık şartları nelerdir?",
    "answer": "AI tarafından üretilen cevap...",
    "confidence_score": 0.85,
    "sources": [...],
    "credit_info": {
      "credits_used": 2,
      "remaining_balance": 23
    },
    "stats": {
      "search_time_ms": 150,
      "generation_time_ms": 800
    }
  }
}
```

**Yetersiz Kredi Hatası:**
```json
{
  "detail": {
    "error": "insufficient_credits",
    "message": "Krediniz bu sorgu için yeterli değil", 
    "required_credits": 4,
    "current_balance": 2,
    "query": "uzun sorgu metni..."
  }
}
```

## 🎯 Özel Durumlar

### Admin Kullanıcılar
- Kredi kontrolü bypass edilir
- Unlimited işlem yapabilir
- Response'da `"admin_user": true` flag'i gelir

### Otomatik Kredi İadesi
Şu durumlarda kredi otomatik iade edilir:
- AI servisi hatası
- Veritabanı bağlantı hatası
- Rate limit aşımı
- Sistem hataları

### Rate Limiting ile İlişki
- Kredi sistemi mevcut 30 req/min limit ile beraber çalışır
- Her iki kontrol de geçilmesi gerekir
- Rate limit admin kullanıcılar için de aktif

## 🔗 Database Schema

```sql
-- Kredi transaction tablosu
CREATE TABLE user_credits (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    transaction_type TEXT CHECK (transaction_type IN ('initial', 'deduction', 'refund', 'admin_add', 'admin_set')),
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    description TEXT,
    query_id TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Kullanıcı bakiye view'i  
CREATE VIEW user_credit_balance AS 
SELECT 
    user_id, 
    COALESCE(SUM(amount), 0) as current_balance,
    COUNT(*) as transaction_count,
    MAX(created_at) as last_transaction
FROM user_credits 
GROUP BY user_id;
```

## 🚀 Kurulum ve Aktivasyon

Kredi sistemi MevzuatGPT ile birlikte otomatik olarak aktif hale gelir. Yeni kullanıcılar kayıt olduklarında otomatik olarak 30 kredi alırlar.

### Yönetici İşlemleri
1. Admin panelinden kullanıcılara ek kredi tanımlanabilir
2. Toplu kredi işlemleri yapılabilir
3. Detaylı raporlama mevcuttur

### Monitoring
- Tüm kredi işlemleri loglanır
- Transaction geçmişi saklanır
- Admin dashboard üzerinden takip edilebilir

## ⚙️ Yapılandırma

### Kredi Miktarları (CreditService)
```python
self.initial_credit_amount = 30      # Yeni kullanıcı kredisi
self.base_credit_cost = 1            # Her sorgu temel kredi
self.character_threshold = 100       # Ek kredi için karakter eşiği
```

### Değiştirilebilir Parametreler
- Başlangıç kredi miktarı
- Karakter bazlı ek kredi eşiği
- Admin unlimited bypass

Bu sistem sayesinde kullanım kontrolü, fair use policy ve sürdürülebilirlik sağlanır.