# 📄 PDF Yükleme Rehberi - MevzuatGPT

Bu rehber, MevzuatGPT sistemine PDF belge yükleme işlemini ve kabul edilen metadata alanlarını açıklar.

## 🔗 Endpoint Bilgileri

**POST** `/api/admin/upload-document`

- **Yetkilendirme:** Admin rolü gerekli
- **Content-Type:** `multipart/form-data`
- **Authorization:** `Bearer <admin-jwt-token>`

## 📋 Form Data Alanları

### ✅ Zorunlu Alanlar

| Alan | Tür | Açıklama | Sınırlar |
|------|-----|----------|----------|
| `file` | File | PDF dosyası | .pdf uzantılı olmalı |
| `title` | String | Belge başlığı | 1-500 karakter |

### 🔧 İsteğe Bağlı Alanlar

| Alan | Tür | Açıklama | Sınırlar |
|------|-----|----------|----------|
| `category` | String | Belge kategorisi | Max 100 karakter |
| `description` | String | Belge açıklaması | Max 2000 karakter |
| `keywords` | String | Anahtar kelimeler | Virgülle ayrılmış |
| `source_institution` | String | Kaynak kurum | Max 200 karakter |
| `publish_date` | String | Yayın tarihi | YYYY-MM-DD formatında |

## 🎯 Postman Örnek İstek

### Headers
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: multipart/form-data
```

### Form-data
```
file: [PDF dosyası seç]
title: "2023 Yılı Bütçe Kanunu"
category: "Maliye Hukuku"
description: "2023 mali yılına ait merkezi yönetim bütçe kanunu metni"
keywords: "bütçe,maliye,2023,kanun,gelir,gider,TBMM"
source_institution: "Türkiye Büyük Millet Meclisi"
publish_date: "2023-01-01"
```

## 📝 Kullanım Örnekleri

### Örnek 1: Kanun Metni
```
title: "5510 Sayılı Sosyal Sigortalar ve Genel Sağlık Sigortası Kanunu"
category: "Sosyal Güvenlik Hukuku"
description: "Sosyal sigortalar ve genel sağlık sigortası ile ilgili düzenlemeler"
keywords: "sosyal sigorta,sağlık sigortası,5510,SGK,prim"
source_institution: "TBMM"
publish_date: "2006-05-31"
```

### Örnek 2: Yönetmelik
```
title: "İşyeri Hekimi ve Diğer Sağlık Personelinin Görev, Yetki ve Sorumluluklarına İlişkin Yönetmelik"
category: "İş Sağlığı ve Güvenliği"
description: "İşyeri hekimlerinin görev, yetki ve sorumluluklarını düzenleyen yönetmelik"
keywords: "işyeri hekimi,iş güvenliği,sağlık personeli,yönetmelik"
source_institution: "Çalışma ve Sosyal Güvenlik Bakanlığı"
publish_date: "2013-07-10"
```

### Örnek 3: Tebliğ
```
title: "Kurumlar Vergisi Genel Tebliği (Seri No: 1)"
category: "Vergi Hukuku"
description: "2023 yılı kurumlar vergisi uygulamalarına ilişkin açıklamalar"
keywords: "kurumlar vergisi,tebliğ,vergi,2023"
source_institution: "Gelir İdaresi Başkanlığı"
publish_date: "2023-01-15"
```

## 🔄 İşlem Süreci

### 1. **Upload Aşaması**
- PDF dosyası Bunny.net CDN'e yüklenir
- Dosya URL'i alınır
- İstek başarılı ise HTTP 200 döner

### 2. **Metadata Kayıt**
- Belge bilgileri PostgreSQL'e kaydedilir
- Unique document ID oluşturulur
- Yükleyen kullanıcı bilgisi eklenir

### 3. **Arka Plan İşlemi**
- Celery task tetiklenir
- PDF'den metin çıkarılır (PyPDF2)
- Metin parçalara bölünür (LangChain)
- OpenAI embeddings oluşturulur
- Vector veritabanına (pgvector) kaydedilir

## ✅ Başarılı Cevap Örneği

```json
{
    "success": true,
    "data": {
        "document_id": "550e8400-e29b-41d4-a716-446655440000",
        "message": "Document uploaded successfully and queued for processing",
        "file_url": "https://cdn.bunny.net/mevzuatgpt/documents/belge.pdf",
        "processing_status": "pending"
    }
}
```

## ❌ Hata Durumları

### Dosya Tipi Hatası
```json
{
    "success": false,
    "error": {
        "message": "Only PDF files are allowed",
        "code": "INVALID_FILE_TYPE"
    }
}
```

### Yetkilendirme Hatası
```json
{
    "detail": "Admin yetkisi gerekli"
}
```

### Doğrulama Hatası
```json
{
    "detail": [
        {
            "loc": ["body", "title"],
            "msg": "field required",
            "type": "value_error.missing"
        }
    ]
}
```

## 🔍 İşlem Sonrası Takip

### Belge Durumunu Kontrol Etme
```http
GET /api/admin/documents/{document_id}
Authorization: Bearer <token>
```

### İşlem Durumları
- `pending` - Beklemede
- `processing` - İşleniyor
- `completed` - Tamamlandı
- `failed` - Başarısız

## 💡 İpuçları

1. **Dosya Boyutu:** Çok büyük PDF'ler yavaş işlenebilir
2. **Anahtar Kelimeler:** Arama performansı için iyi anahtar kelimeler ekleyin
3. **Kategori:** Tutarlı kategoriler kullanın (örn: "Vergi Hukuku", "İş Hukuku")
4. **Tarih Formatı:** Mutlaka YYYY-MM-DD formatını kullanın
5. **Açıklama:** Detaylı açıklamalar arama sonuçlarını iyileştirir

## 🔧 Teknik Detaylar

- **Max Dosya Boyutu:** Sistem sınırına bağlı
- **Desteklenen Format:** Sadece PDF
- **Storage:** Bunny.net CDN
- **Database:** PostgreSQL + pgvector
- **Background Jobs:** Redis + Celery
- **AI Model:** OpenAI text-embedding-3-large

---

**💬 Not:** Bu endpoint sadece admin rolündeki kullanıcılar tarafından kullanılabilir. User rolündeki kullanıcılar sadece arama yapabilir.