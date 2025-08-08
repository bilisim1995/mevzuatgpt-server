# 🚀 MevzuatGPT API Endpoints Rehberi

Bu belge, MevzuatGPT uygulamasının tüm API endpoint'lerini, istek/cevap örnekleriyle birlikte açıklar.

## 🔧 Base URL

**Replit Platformu için:**
```
https://[repl-name]--[username].replit.dev
```

**Yerel Development için:**
```
http://localhost:5000
```

> ℹ️ **Not:** Replit URL'ini workspace'te Console tool'dan veya browser URL'inden kopyalayabilirsin.

## 🔐 Kimlik Doğrulama

Çoğu endpoint, Authorization header'ında Bearer token gerektirir:
```
Authorization: Bearer <your-jwt-token>
```

---

## 📋 İÇİNDEKİLER

- [Kimlik Doğrulama Endpoints](#kimlik-doğrulama-endpoints)
- [Kullanıcı Endpoints](#kullanıcı-endpoints) 
- [Admin Endpoints](#admin-endpoints)
- [Sistem Endpoints](#sistem-endpoints)

---

## 🔑 KİMLİK DOĞRULAMA ENDPOINTS

### 1. Kullanıcı Kaydı

**POST** `/api/auth/register`

Yeni kullanıcı kaydı oluşturur.

**İstek Örneği:**
```json
{
    "email": "user@example.com",
    "password": "strongPassword123",
    "full_name": "Ahmet Yılmaz"
}
```

**Cevap Örneği:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "full_name": "Ahmet Yılmaz",
        "role": "user",
        "created_at": "2024-01-15T10:30:00Z"
    }
}
```

### 2. Kullanıcı Girişi

**POST** `/api/auth/login`

Mevcut kullanıcının sisteme girişini sağlar.

**İstek Örneği:**
```json
{
    "email": "user@example.com",
    "password": "strongPassword123"
}
```

**Cevap Örneği:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "full_name": "Ahmet Yılmaz",
        "role": "user"
    }
}
```

### 3. Kullanıcı Bilgilerini Getir

**GET** `/api/auth/me`

Giriş yapmış kullanıcının bilgilerini döndürür.

**Headers:**
```
Authorization: Bearer <token>
```

**Cevap Örneği:**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "Ahmet Yılmaz",
    "role": "user",
    "created_at": "2024-01-15T10:30:00Z"
}
```

### 4. Token Doğrulama

**GET** `/api/auth/verify-token`

Mevcut token'ın geçerli olup olmadığını kontrol eder.

**Headers:**
```
Authorization: Bearer <token>
```

**Cevap Örneği:**
```json
{
    "valid": true,
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "role": "user"
    },
    "message": "Token geçerli"
}
```

### 5. Çıkış Yap

**POST** `/api/auth/logout`

Kullanıcının oturumunu sonlandırır.

**Cevap Örneği:**
```json
{
    "message": "Başarıyla çıkış yapıldı",
    "detail": "Token'ı client tarafında kaldırın"
}
```

---

## 👤 KULLANICI ENDPOINTS

### 1. Belge Arama

**POST** `/api/user/search`

Yüklenen belgelerde semantik arama yapar.

**Headers:**
```
Authorization: Bearer <token>
```

**İstek Örneği:**
```json
{
    "query": "iş sözleşmesi fesih süreleri",
    "limit": 10,
    "similarity_threshold": 0.7
}
```

**Cevap Örneği:**
```json
{
    "query": "iş sözleşmesi fesih süreleri",
    "results": [
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "content": "İş sözleşmesinin feshi durumunda işveren...",
            "similarity": 0.85,
            "document_title": "İş Kanunu",
            "document_filename": "is_kanunu.pdf",
            "chunk_index": 15
        }
    ],
    "total_results": 1,
    "execution_time": 0.234
}
```

### 2. Arama Geçmişi

**GET** `/api/user/search-history`

Kullanıcının arama geçmişini getir.

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `limit` (opsiyonel): Sonuç sayısı (varsayılan: 50)
- `offset` (opsiyonel): Başlangıç noktası (varsayılan: 0)

**Cevap Örneği:**
```json
{
    "searches": [
        {
            "id": "789e0123-e89b-12d3-a456-426614174000",
            "query": "iş sözleşmesi fesih süreleri",
            "results_count": 5,
            "created_at": "2024-01-15T14:30:00Z"
        }
    ],
    "total": 1,
    "limit": 50,
    "offset": 0
}
```

### 3. Belge Detayı

**GET** `/api/user/document/{document_id}`

Belirli bir belgenin detay bilgilerini getir.

**Headers:**
```
Authorization: Bearer <token>
```

**Cevap Örneği:**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "İş Kanunu",
    "filename": "is_kanunu.pdf",
    "upload_date": "2024-01-15T10:30:00Z",
    "status": "completed",
    "content_preview": "Bu kanunun amacı...",
    "metadata": {
        "category": "hukuk",
        "pages": 120
    }
}
```

---

## 🔧 ADMİN ENDPOINTS

### 1. Belge Yükleme

**POST** `/api/admin/upload-document`

PDF belge yükler ve işleme kuyruğuna ekler.

**Headers:**
```
Authorization: Bearer <admin-token>
Content-Type: multipart/form-data
```

**Form Data:**
```
file: <PDF dosyası>
title: "Belge Başlığı"
category: "hukuk" (opsiyonel)
```

**Cevap Örneği:**
```json
{
    "message": "Belge başarıyla yüklendi",
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "task_id": "celery-task-123456"
}
```

### 2. Tüm Belgeleri Listele

**GET** `/api/admin/documents`

Sistemdeki tüm belgeleri listeler.

**Headers:**
```
Authorization: Bearer <admin-token>
```

**Query Parameters:**
- `status` (opsiyonel): "processing", "completed", "failed"
- `limit` (opsiyonel): Sonuç sayısı (varsayılan: 50)
- `offset` (opsiyonel): Başlangıç noktası (varsayılan: 0)

**Cevap Örneği:**
```json
{
    "documents": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "İş Kanunu",
            "filename": "is_kanunu.pdf",
            "status": "completed",
            "upload_date": "2024-01-15T10:30:00Z",
            "uploaded_by": "admin@example.com"
        }
    ],
    "total": 1,
    "limit": 50,
    "offset": 0
}
```

### 3. Belge Sil (Cascade)

**DELETE** `/api/admin/documents/{document_id}`

Belgeyi ve tüm ilişkili verilerini tamamen siler (fiziksel dosya + embeddings + database).

**Headers:**
```
Authorization: Bearer <admin-token>
Content-Type: application/json
```

**URL Parameters:**
```
document_id: Silinecek belgenin UUID'si
```

**Cevap Örneği:**
```json
{
    "success": true,
    "message": "Document deleted successfully",
    "data": {
        "document_id": "3ce3678c-f15b-4970-b717-8500832986d2",
        "document_title": "Kısa Vadeli Sigorta Mevzuat",
        "embeddings_deleted": 17,
        "physical_file_deleted": true,
        "file_url": "https://cdn.mevzuatgpt.org/documents/file.pdf"
    }
}
```

**Silme Süreci:**
1. 🔍 Document bilgilerini al
2. 🗂️ Tüm embeddings'leri sil (foreign key)
3. 💾 Fiziksel PDF dosyasını Bunny.net'ten sil
4. 📄 Document kaydını veritabanından sil

**Hata Cevapları:**
- **404**: Document bulunamadı
- **401**: Yetkisiz erişim  
- **500**: Silme işlemi başarısız

### 4. Belge İşleme Durumu

**GET** `/api/admin/documents/{document_id}/status`

Belge işleme durumunu kontrol eder.

**Headers:**
```
Authorization: Bearer <admin-token>
```

**Cevap Örneği:**
```json
{
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "progress": 100,
    "chunks_processed": 45,
    "total_chunks": 45,
    "processing_time": 120.5,
    "error_message": null
}
```

### 5. Kullanıcı Yönetimi

**GET** `/api/admin/users`

Sistem kullanıcılarını listeler.

**Headers:**
```
Authorization: Bearer <admin-token>
```

**Cevap Örneği:**
```json
{
    "users": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "full_name": "Ahmet Yılmaz",
            "role": "user",
            "created_at": "2024-01-15T10:30:00Z",
            "last_login": "2024-01-15T14:30:00Z"
        }
    ],
    "total": 1
}
```

### 6. Kullanıcı Rolü Güncelle

**PATCH** `/api/admin/users/{user_id}/role`

Kullanıcının rolünü günceller.

**Headers:**
```
Authorization: Bearer <admin-token>
```

**İstek Örneği:**
```json
{
    "role": "admin"
}
```

**Cevap Örneği:**
```json
{
    "message": "Kullanıcı rolü güncellendi",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "new_role": "admin"
}
```

### 7. Sistem İstatistikleri

**GET** `/api/admin/stats`

Sistem kullanım istatistiklerini döndürür.

**Headers:**
```
Authorization: Bearer <admin-token>
```

**Cevap Örneği:**
```json
{
    "total_documents": 25,
    "total_users": 12,
    "total_searches": 340,
    "storage_used": "1.2 GB",
    "active_users_today": 5,
    "popular_queries": [
        "iş sözleşmesi",
        "vergi kanunu",
        "ticaret hukuku"
    ]
}
```

---

## 🔍 SİSTEM ENDPOINTS

### 1. Sistem Durumu

**GET** `/health`

Sistem sağlık kontrolü.

**Cevap Örneği:**
```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0",
    "services": {
        "database": "connected",
        "redis": "connected",
        "openai": "available",
        "storage": "available"
    }
}
```

### 2. API Dokümantasyon

**GET** `/docs`

Interaktif API dokümantasyonunu görüntüler (Swagger UI).

### 3. OpenAPI Schema

**GET** `/openapi.json`

OpenAPI schema'sını JSON formatında döndürür.

---

## ⚠️ HATA KODLARI

### HTTP Status Kodları

- **200 OK**: İstek başarılı
- **201 Created**: Kaynak oluşturuldu
- **400 Bad Request**: Geçersiz istek
- **401 Unauthorized**: Kimlik doğrulama gerekli
- **403 Forbidden**: Erişim izni yok
- **404 Not Found**: Kaynak bulunamadı
- **422 Unprocessable Entity**: Veri doğrulama hatası
- **429 Too Many Requests**: Rate limit aşıldı
- **500 Internal Server Error**: Sunucu hatası

### Hata Yanıt Formatı

```json
{
    "detail": "Hata açıklaması",
    "error_code": "SPECIFIC_ERROR_CODE",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### Yaygın Hata Örnekleri

**Geçersiz Token:**
```json
{
    "detail": "Token geçersiz veya süresi dolmuş",
    "error_code": "INVALID_TOKEN"
}
```

**Dosya Boyutu Aşımı:**
```json
{
    "detail": "Dosya boyutu 50MB'dan büyük olamaz",
    "error_code": "FILE_TOO_LARGE"
}
```

**Geçersiz Dosya Türü:**
```json
{
    "detail": "Sadece PDF dosyaları desteklenir",
    "error_code": "INVALID_FILE_TYPE"
}
```

---

## 🔧 KULLANIM İPUÇLARI

### Rate Limiting
- Kimlik doğrulama endpoint'leri: 5 istek/dakika
- Arama endpoint'leri: 20 istek/dakika
- Diğer endpoint'ler: 100 istek/dakika

### Dosya Yükleme
- Maksimum dosya boyutu: 50MB
- Desteklenen format: PDF
- Önerilen dosya adı formatı: `kategori_belge_adi.pdf`

### Arama Optimizasyonu
- Türkçe anahtar kelimeler kullanın
- Çok kısa sorgulardan kaçının (min 3 kelime)
- Similarity threshold: 0.6-0.8 arası önerilir

### Güvenlik
- Token'ları güvenli yerde saklayın
- HTTPS kullanın (production)
- API anahtarlarını paylaşmayın

---

Bu dökümantasyon, MevzuatGPT API'sinin tüm özelliklerini kapsar. Sorularınız için sistem yöneticisine başvurun.