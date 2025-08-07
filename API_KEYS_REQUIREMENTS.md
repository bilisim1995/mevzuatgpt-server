# 🔑 MevzuatGPT API Anahtarları ve Servis Gereksinimleri

Bu dosya, MevzuatGPT uygulamasının tam fonksiyonel çalışması için gerekli tüm API anahtarları ve servis bilgilerini listeler.

## 🚀 ÖNCELİKLİ GEREKSİNİMLER (Zorunlu)

### 1. OpenAI API 
**Neden gerekli:** Belge içeriklerini vektör haline çevirmek ve arama yapmak için
- **Nereden alınır:** https://platform.openai.com/api-keys
- **Format:** `sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Kullanım:** Embedding (text-embedding-3-large) ve ChatGPT (gpt-4o)
- **Tahmini maliyet:** $0.01-0.10 per 1000 token

### 2. Bunny.net Storage
**Neden gerekli:** PDF dosyalarını depolamak ve CDN üzerinden sunmak için
- **Nereden alınır:** https://panel.bunny.net/
- **Gerekli bilgiler:**
  - Storage API Key: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
  - Storage Zone Name: `your-zone-name`
  - Storage Endpoint: `https://your-zone.b-cdn.net`
- **Kullanım:** PDF upload, storage, download
- **Tahmini maliyet:** $0.01/GB storage + $0.01/GB bandwidth

## 🔧 OPSIYONEL GEREKSİNİMLER

### 3. Supabase (ZORUNLU - Ana Veritabanı ve Auth)
**Neden gerekli:** Kullanıcı yönetimi, veritabanı ve vektör arama için
- **Nereden alınır:** https://app.supabase.com/
- **Gerekli bilgiler:**
  - Project URL: `https://xxxxxxxxxxxxxxxxx.supabase.co`
  - Anon/Public Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
  - Service Role Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
  - Database URL: `postgresql://postgres.xxxxxxxxx:password@aws-0-eu-central-1.pooler.supabase.com:5432/postgres`
- **Kurulum:** Vector extension'ını etkinleştirin, SQL şemalarını çalıştırın

### 4. Redis Cloud (ZORUNLU - Background Tasks için)
**Neden gerekli:** Celery background tasks ve caching için
- **Nereden alınır:** https://app.redislabs.com/
- **Format:** `redis://default:password@redis-12345.c123.us-east-1-4.ec2.cloud.redislabs.com:12345`
- **Kullanım:** PDF işleme, embedding oluşturma, async tasks

## 📋 HIZLI KURULUM REHBERİ

### Adım 1: .env Dosyası Oluşturun
```bash
cp .env.example .env
```

### Adım 2: Zorunlu API Anahtarlarını Doldurun
1. OpenAI API anahtarınızı `OPENAI_API_KEY` satırına yazın
2. Bunny.net bilgilerinizi ilgili satırlara yazın

### Adım 3: Opsiyonel Servisleri Yapılandırın
- Supabase kullanmak istiyorsanız ilgili anahtarları doldurun
- Redis kullanmak istiyorsanız bağlantı bilgilerini güncelleyin

## 🔒 GÜVENLİK NOTLARI

- ⚠️ `.env` dosyasını asla Git'e commit etmeyin
- 🔐 API anahtarlarını kimseyle paylaşmayın
- 🔄 Düzenli olarak anahtarlarınızı yenileyin
- 📊 API kullanım limitlerini takip edin

## 🆘 SORUN GİDERME

### OpenAI API Sorunları
- API anahtarının aktif olduğundan emin olun
- Billing hesabınızda kredi bulunduğunu kontrol edin
- Rate limit aşımı kontrolü yapın

### Bunny.net Sorunları
- Storage zone'un aktif olduğunu kontrol edin
- API key'in doğru permissions'a sahip olduğunu doğrulayın
- Endpoint URL'in doğru formatta olduğunu kontrol edin

### Genel Bağlantı Sorunları
- İnternet bağlantınızı kontrol edin
- Firewall ayarlarını gözden geçirin
- Logs'ları inceleyerek hata mesajlarını takip edin

---

Bu bilgileri .env dosyasına girdikten sonra uygulamayı yeniden başlatmayı unutmayın!