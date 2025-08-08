# Replit Secrets Temizleme ve .env Kullanım Rehberi

## Neden Secrets'ı Temizliyoruz?

Sistem şu anda API anahtarlarını hem Replit Secrets hem de .env dosyasından çekmeye çalışıyor. Bu karışıklığı önlemek için sadece .env dosyasını kullanacağız.

## Secrets Temizleme Adımları

### Yöntem 1: Tek Tek Silme
1. Replit editor'de sol panelden **"Secrets"** sekmesini açın
2. `OPENAI_API_KEY` satırının yanındaki **üç nokta (⋮)** menüsüne tıklayın
3. **"Delete"** seçeneğini seçin
4. `GROQ_API_KEY` için aynı işlemi tekrarlayın

### Yöntem 2: Toplu Silme
1. Secrets panelinde en alttaki **"Edit as .env"** butonuna tıklayın
2. Tüm içeriği silin (Ctrl+A → Delete)
3. **"Save"** butonuna tıklayın

## .env Dosyası Kontrolü

Secrets silindikten sonra sistem otomatik olarak `.env` dosyasından API anahtarlarını okuyacak.

### Mevcut .env İçeriği:
```env
# OpenAI API
OPENAI_API_KEY=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

# Groq API (eklenecek)
GROQ_API_KEY=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
AI_PROVIDER=groq
```

## Test ve Doğrulama

Secrets temizledikten sonra:

1. Workflow'ları yeniden başlatın:
   - `MevzuatGPT API Server` → Restart
   - `Celery Worker` → Restart

2. API bağlantılarını test edin:
   ```bash
   python tests/production_ready_test.py
   ```

## Beklenen Sonuç

✅ **OpenAI API**: .env'den key okuyacak  
✅ **Groq API**: .env'den key okuyacak  
✅ **Environment Cache**: Temizlenmiş olacak  
✅ **Sistem**: Tamamen .env tabanlı çalışacak

## Sorun Giderme

Eğer sistem hala eski key'leri kullanıyorsa:
1. Browser cache'ini temizleyin
2. Replit workspace'ini yeniden başlatın
3. `.env` dosyasındaki key'lerin doğruluğunu kontrol edin

## Güvenlik Notu

.env dosyası projede kalacağı için key'lerin güvenliği önemli. Bu dosya `.gitignore`'da olmalı ve proje public paylaşılmamalı.