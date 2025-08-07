# 🔑 MevzuatGPT API Anahtarları ve Servis Gereksinimleri

Bu dosya, MevzuatGPT uygulamasının tam fonksiyonel çalışması için gerekli tüm API anahtarları ve servis bilgilerini listeler.

## 🚀 ZORUNLU GEREKSİNİMLER

### 1. OpenAI API 
**Neden gerekli:** Belge içeriklerini vektör haline çevirmek ve AI sohbet için
- **Nereden alınır:** https://platform.openai.com/api-keys
- **Format:** `sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Kullanım:** 
  - Embedding (text-embedding-3-large) - metinleri vektöre çevirme
  - ChatGPT (gpt-4o) - kullanıcı sorularını yanıtlama
- **Tahmini maliyet:** $0.01-0.10 per 1000 token

### 2. Bunny.net Storage
**Neden gerekli:** PDF dosyalarını depolamak ve CDN üzerinden sunmak için
- **Nereden alınır:** https://panel.bunny.net/
- **Gerekli bilgiler:**
  - Storage API Key: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
  - Storage Zone Name: `your-zone-name`
  - Storage Region: `de` (Almanya - en yakın)
  - Storage Endpoint: `https://your-zone.b-cdn.net`
- **Kullanım:** PDF upload, depolama, indirme
- **Tahmini maliyet:** $0.01/GB depolama + $0.01/GB bandwidth

### 3. Supabase (ZORUNLU - Ana Veritabanı ve Auth)
**Neden gerekli:** Kullanıcı yönetimi, veritabanı ve vektör arama için
- **Nereden alınır:** https://app.supabase.com/
- **Gerekli bilgiler:**
  - Project URL: `https://xxxxxxxxxxxxxxxxx.supabase.co`
  - Anon/Public Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
  - Service Role Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
  - Database URL: `postgresql://postgres.xxxxxxxxx:password@aws-0-eu-central-1.pooler.supabase.com:5432/postgres`
- **Kurulum:** Vector extension'ını etkinleştirin, SQL şemalarını çalıştırın
- **Kullanım:** Kullanıcı auth, belge metadata, vektör arama

### 4. Redis Cloud (ZORUNLU - Background Tasks için)
**Neden gerekli:** Celery background tasks ve caching için
- **Nereden alınır:** https://app.redislabs.com/
- **Format:** `redis://default:password@redis-12345.c123.us-east-1-4.ec2.cloud.redislabs.com:12345`
- **Kullanım:** PDF işleme, embedding oluşturma, async tasks
- **Tahmini maliyet:** Ücretsiz katman 30MB'a kadar

## 📋 HIZLI KURULUM REHBERİ

### Adım 1: .env Dosyası Oluşturun
```bash
cp .env.example .env
```

### Adım 2: Zorunlu API Anahtarlarını Doldurun
1. **OpenAI**: `OPENAI_API_KEY` satırına API anahtarınızı yazın
2. **Bunny.net**: Storage bilgilerinizi ilgili satırlara yazın
3. **Supabase**: Project URL ve API key'leri yazın
4. **Redis Cloud**: Bağlantı string'ini yazın

### Adım 3: Supabase'i Kurun
1. Supabase projesinde Vector extension'ını aktifleştirin
2. `destek/supabase_kurulum.md` dosyasındaki SQL kodlarını çalıştırın
3. İlk admin kullanıcıyı Supabase Auth panel'den oluşturun

### Adım 4: Uygulamayı Başlatın
```bash
python app.py server
```

## 🔒 GÜVENLİK NOTLARI

- ⚠️ `.env` dosyasını asla Git'e commit etmeyin
- 🔐 API anahtarlarını kimseyle paylaşmayın
- 🔄 Düzenli olarak anahtarlarınızı yenileyin
- 📊 API kullanım limitlerini takip edin
- 🛡️ Supabase RLS politikalarının aktif olduğundan emin olun

## 🆘 SORUN GİDERME

### OpenAI API Sorunları
- API anahtarının aktif olduğundan emin olun
- Billing hesabınızda kredi bulunduğunu kontrol edin
- Rate limit aşımı kontrolü yapın
- Model adlarının doğru olduğunu kontrol edin

### Bunny.net Sorunları
- Storage zone'un aktif olduğunu kontrol edin
- API key'in doğru permissions'a sahip olduğunu doğrulayın
- Endpoint URL'in doğru formatta olduğunu kontrol edin
- Dosya boyutu limitlerini kontrol edin

### Supabase Sorunları
- RLS politikalarının doğru kurulduğunu kontrol edin
- Vector extension'ının aktif olduğunu doğrulayın
- Database URL'in doğru olduğunu kontrol edin
- API key'lerin doğru permissions'a sahip olduğunu kontrol edin

### Redis Cloud Sorunları
- Bağlantı string'inin doğru olduğunu kontrol edin
- SSL sertifikası gereksinimlerini kontrol edin
- Memory limitlerini ve kullanımı takip edin

### Genel Bağlantı Sorunları
- İnternet bağlantınızı kontrol edin
- Firewall ayarlarını gözden geçirin
- Logs'ları inceleyerek hata mesajlarını takip edin
- API servislerinin status sayfalarını kontrol edin

## 📞 DESTEK

Sorun yaşıyorsanız:
1. Önce logs'ları kontrol edin: `logs/app.log` ve `logs/error.log`
2. API servislerinin status sayfalarını kontrol edin
3. .env dosyasındaki değerleri tekrar kontrol edin
4. Gerekirse API anahtarlarını yenileyin

---

Bu bilgileri .env dosyasına girdikten sonra uygulamayı yeniden başlatmayı unutmayın!