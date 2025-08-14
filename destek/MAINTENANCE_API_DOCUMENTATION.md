# Bakım Modu API Dokümantasyonu

## User Endpoint (Public)

### GET /api/maintenance/status

Sistem bakım durumunu kontrol etmek için kullanılır. Authentication gerektirmez.

**Request:**
```bash
curl -X GET "https://your-domain.com/api/maintenance/status" \
     -H "Accept: application/json"
```

**Response Format:**
```json
{
  "success": true,
  "timestamp": "2025-08-11T18:45:00.123456",
  "data": {
    "is_enabled": boolean,
    "title": "string",
    "message": "string", 
    "start_time": "datetime|null",
    "end_time": "datetime|null"
  }
}
```

**Response Examples:**

### 1. Sistem Normal Çalışıyor
```json
{
  "success": true,
  "timestamp": "2025-08-11T18:45:00.123456",
  "data": {
    "is_enabled": false,
    "title": "Sistem Aktif",
    "message": "Sistem normal çalışıyor.",
    "start_time": null,
    "end_time": null
  }
}
```

### 2. Sistem Bakımda
```json
{
  "success": true,
  "timestamp": "2025-08-11T18:45:00.123456", 
  "data": {
    "is_enabled": true,
    "title": "Planlı Sistem Bakımı",
    "message": "Sistem 22:00-02:00 arası bakımda. Bu süre zarfında hizmet alamayabilirsiniz.",
    "start_time": "2025-08-11T22:00:00Z",
    "end_time": "2025-08-12T02:00:00Z"
  }
}
```

### 3. Hata Durumu
```json
{
  "success": true,
  "timestamp": "2025-08-11T18:45:00.123456",
  "data": {
    "is_enabled": false,
    "title": "Sistem Durumu Bilinmiyor", 
    "message": "Sistem durumu kontrol edilemiyor, lütfen daha sonra tekrar deneyin.",
    "start_time": null,
    "end_time": null
  }
}
```

## Admin Endpoints (Authentication Required)

### GET /api/admin/maintenance

Admin bakım modu detaylarını görüntüler. Admin authentication gerektirir.

**Headers:**
```
Authorization: Bearer <admin_token>
Accept: application/json
```

**Response:**
```json
{
  "success": true,
  "timestamp": "2025-08-11T18:45:00.123456",
  "data": {
    "id": "uuid",
    "is_enabled": boolean,
    "title": "string",
    "message": "string",
    "start_time": "datetime|null", 
    "end_time": "datetime|null",
    "updated_by": "uuid|null",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

### PUT /api/admin/maintenance

Admin bakım modunu günceller. Admin authentication gerektirir.

**Headers:**
```
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "is_enabled": true,
  "title": "Planlı Sistem Bakımı",
  "message": "Sistem 22:00-02:00 arası bakımda.",
  "start_time": "2025-08-11T22:00:00Z",
  "end_time": "2025-08-12T02:00:00Z"
}
```

**Response:** Same as GET /api/admin/maintenance

## Field Açıklamaları

- `is_enabled`: Bakım modu aktif mi? (boolean)
- `title`: Bakım modu başlığı (string, max 200 karakter)
- `message`: Kullanıcıya gösterilecek mesaj (text)
- `start_time`: Bakım başlangıç zamanı (ISO datetime veya null)
- `end_time`: Bakım bitiş zamanı (ISO datetime veya null)
- `updated_by`: Son güncelleyen admin user ID (UUID)
- `created_at`: Kayıt oluşturma zamanı
- `updated_at`: Son güncelleme zamanı

## Frontend Kullanımı

Frontend uygulamalarında bu endpoint'i kullanarak:

1. Uygulama açılışında bakım durumunu kontrol edin
2. is_enabled: true ise bakım sayfası gösterin
3. title ve message alanlarını kullanıcıya gösterin
4. start_time ve end_time varsa süre bilgisi verin
5. Periyodik olarak (5-10 dakikada bir) durumu yeniden kontrol edin