# MevzuatGPT - Dosya Karşılaştırma API Dokümantasyonu

## 📋 Genel Bakış

MevzuatGPT sistemi artık **dosya yükleme (file upload)** ile mevzuat karşılaştırma yapabilir. Sistem **OCR** ve **NLP** desteği ile PDF, Word, Resim formatlarındaki dosyalardan metin çıkarır ve AI ile karşılaştırır.

---

## 🚀 Endpoint

### POST `/api/user/compare-documents-upload`

Dosya yükleyerek mevzuat karşılaştırma (OCR + NLP Destekli)

---

## 📁 Desteklenen Dosya Formatları

| Format | Uzantılar | İşlem Yöntemi |
|--------|-----------|---------------|
| **PDF** | `.pdf` | pdfplumber ile metin çıkarma |
| **Word** | `.docx`, `.doc` | python-docx ile metin çıkarma |
| **Resim** | `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.webp` | Tesseract OCR 5.5 ile metin çıkarma |
| **Text** | `.txt`, `.md` | Doğrudan okuma |

---

## 🔐 Kimlik Doğrulama

Bearer Token ile kimlik doğrulama gereklidir:

```http
Authorization: Bearer <JWT_TOKEN>
```

---

## 📤 İstek Formatı

**Content-Type:** `multipart/form-data`

### Form Parametreleri

| Parametre | Tip | Zorunlu | Açıklama |
|-----------|-----|---------|----------|
| `old_file` | File | ✅ Evet | Eski mevzuat dosyası (max 10MB) |
| `new_file` | File | ✅ Evet | Yeni mevzuat dosyası (max 10MB) |
| `analysis_level` | String | ❌ Hayır | Analiz seviyesi (varsayılan: `normal`) |

### Analiz Seviyeleri

- **`yuzeysel`**: Hızlı özet (5-10 madde)
- **`normal`**: Standart analiz (varsayılan)
- **`detayli`**: Kapsamlı inceleme

---

## 💻 Örnek Kullanım

### JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append('old_file', oldFileInput.files[0]);
formData.append('new_file', newFileInput.files[0]);
formData.append('analysis_level', 'detayli');

const response = await fetch('https://api.mevzuatgpt.org/api/user/compare-documents-upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

const result = await response.json();
console.log(result);
```

### Python/Requests

```python
import requests

url = "https://api.mevzuatgpt.org/api/user/compare-documents-upload"
headers = {
    "Authorization": f"Bearer {token}"
}

files = {
    'old_file': open('eski_mevzuat.pdf', 'rb'),
    'new_file': open('yeni_mevzuat.pdf', 'rb')
}

data = {
    'analysis_level': 'detayli'
}

response = requests.post(url, headers=headers, files=files, data=data)
result = response.json()
print(result)
```

### cURL

```bash
curl -X POST "https://api.mevzuatgpt.org/api/user/compare-documents-upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "old_file=@eski_mevzuat.pdf" \
  -F "new_file=@yeni_mevzuat.pdf" \
  -F "analysis_level=detayli"
```

---

## 📥 Yanıt Formatı

### Başarılı Yanıt (200 OK)

```json
{
  "success": true,
  "result": {
    "analysis_level": "detayli",
    "comparison_markdown": "# Mevzuat Karşılaştırma Raporu\n\n## ✅ Eklenen Maddeler\n...",
    "summary": "Bu karşılaştırmada 12 değişiklik tespit edildi...",
    "changes_count": 12,
    "generation_time_ms": 3456
  },
  "old_document_info": {
    "title": "eski_mevzuat.pdf",
    "content_length": 15847,
    "format": "pdf",
    "extraction_method": "pdfplumber",
    "confidence": 0.95
  },
  "new_document_info": {
    "title": "yeni_mevzuat.pdf",
    "content_length": 18234,
    "format": "pdf",
    "extraction_method": "pdfplumber",
    "confidence": 0.95
  },
  "timestamp": "2025-10-07T22:45:00.000Z"
}
```

### Response Alanları

| Alan | Tip | Açıklama |
|------|-----|----------|
| `success` | Boolean | İşlem başarı durumu |
| `result.analysis_level` | String | Kullanılan analiz seviyesi |
| `result.comparison_markdown` | String | Markdown formatında karşılaştırma raporu |
| `result.summary` | String | Değişikliklerin özeti |
| `result.changes_count` | Integer | Toplam değişiklik sayısı |
| `result.generation_time_ms` | Integer | İşlem süresi (milisaniye) |
| `old_document_info` | Object | Eski belge meta bilgileri |
| `new_document_info` | Object | Yeni belge meta bilgileri |
| `timestamp` | DateTime | İşlem zaman damgası |

### Belge Meta Bilgileri

| Alan | Tip | Açıklama |
|------|-----|----------|
| `title` | String | Dosya adı |
| `content_length` | Integer | Çıkarılan metin uzunluğu |
| `format` | String | Dosya formatı (pdf, word, image, text) |
| `extraction_method` | String | Kullanılan çıkarma yöntemi |
| `confidence` | Float | Güven skoru (0.0 - 1.0) |

---

## ⚠️ Hata Kodları

| HTTP Kod | Hata Kodu | Açıklama |
|----------|-----------|----------|
| 400 | `BAD_REQUEST` | Geçersiz analiz seviyesi |
| 401 | `UNAUTHORIZED` | Geçersiz veya eksik token |
| 413 | `PAYLOAD_TOO_LARGE` | Dosya boyutu 10MB'ı aşıyor |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Desteklenmeyen dosya formatı |
| 500 | `FILE_COMPARE_FAILED` | Sunucu hatası |

### Hata Yanıt Örneği

```json
{
  "detail": "Eski dosya çok büyük (15.3 MB). Maksimum 10 MB.",
  "error_code": "PAYLOAD_TOO_LARGE",
  "status_code": 413
}
```

---

## 🎨 Markdown Çıktısı

Karşılaştırma sonuçları Markdown formatında döner:

```markdown
# Mevzuat Karşılaştırma Raporu

## ✅ Eklenen Maddeler
- **MADDE 15**: Yeni düzenleme...

## ❌ Çıkarılan Maddeler
- **MADDE 8**: Eski hüküm...

## 🔄 Değiştirilen Maddeler
- **MADDE 3**: 
  - **Eski**: ...
  - **Yeni**: ...
```

---

## 🔬 OCR ve NLP Özellikleri

### OCR (Optical Character Recognition)

**Resim dosyaları için Tesseract OCR:**

- **Tesseract OCR 5.5** (Ana yöntem)
   - Açık kaynak, güvenli çözüm
   - Doğruluk: ~85%
   - Türkçe dil desteği (tur)
   - Offline çalışma
   - Harici API gerekmez

### NLP (Doğal Dil İşleme)

Metin temizleme özellikleri:
- ✅ Fazla boşluk temizleme
- ✅ Satır sonu normalizasyonu
- ✅ Türkçe karakter koruması
- ✅ Madde numarası düzeltme
- ✅ Encoding tespiti (UTF-8, Windows-1254, ISO-8859-9)

---

## 📊 Performans

| İşlem | Süre (Ortalama) |
|-------|-----------------|
| PDF İşleme | ~1-2 saniye |
| Word İşleme | ~0.5-1 saniye |
| OCR (Resim) | ~3-5 saniye |
| AI Karşılaştırma | ~2-4 saniye |
| **Toplam** | **~6-12 saniye** |

---

## 🔒 Güvenlik

- ✅ Dosya boyutu sınırı: 10MB
- ✅ Format validasyonu
- ✅ JWT kimlik doğrulama
- ✅ Rate limiting (kullanıcı bazlı)
- ✅ Hata logları

---

## 📝 Notlar

1. **Dosya Boyutu**: Maksimum 10MB. Daha büyük dosyalar için önce dosyayı sıkıştırın.

2. **OCR Kalitesi**: Resim kalitesi OCR doğruluğunu etkiler. Net, yüksek çözünürlüklü görseller kullanın.

3. **Türkçe Karakter**: Tüm formatlar Türkçe karakterleri destekler.

4. **Zaman Aşımı**: Büyük dosyalar için işlem ~30 saniye sürebilir.

5. **API Key Gerekmez**: Tesseract OCR kullanıldığı için harici API key'e ihtiyaç yoktur.

---

## 🆕 Yeni Özellikler

### v2.0 (Ekim 2025)
- ✅ Dosya yükleme desteği
- ✅ Tesseract OCR 5.5 ile açık kaynak OCR
- ✅ NLP destekli metin temizleme
- ✅ Multi-format desteği (PDF, Word, Resim)
- ✅ Güven skoru (confidence) hesaplama
- ✅ Extraction method bilgisi
- ✅ Harici API key gerekmez

---

## 📞 Destek

Sorunlar için:
- Email: info@mevzuatgpt.org
- API Dokümantasyon: https://api.mevzuatgpt.org/docs

---

**Son Güncelleme:** 7 Ekim 2025
**API Versiyonu:** 2.0
