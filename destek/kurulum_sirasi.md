# 📚 MevzuatGPT Kurulum Sırası ve Rehber İndeksi

Bu dosya, MevzuatGPT uygulamasını sıfırdan kurmak için gereken tüm adımları sırasıyla listeler.

## 🎯 KURULUM SIRASI

### 1. ADIM: Gerekli Servislere Kaydolun
Önce aşağıdaki servislere kaydolun ve API anahtarlarını alın:

#### Zorunlu Servisler:
- ✅ **OpenAI** → https://platform.openai.com/api-keys
- ✅ **Supabase** → https://app.supabase.com/
- ✅ **Bunny.net** → https://panel.bunny.net/
- ✅ **Redis Cloud** → https://app.redislabs.com/

### 2. ADIM: Supabase'i Kurun
1. 📖 **Rehber**: `destek/supabase_kurulum.md` dosyasını takip edin
2. ⚡ **Önemli**: SQL şemalarını sırasıyla çalıştırın
3. 🔧 Vector extension'ını etkinleştirin
4. 👤 İlk admin kullanıcıyı oluşturun

### 3. ADIM: API Anahtarlarını Yapılandırın
1. 📋 **Rehber**: `destek/api_anahtarlari_rehberi.md` dosyasını okuyun
2. 📄 **Şablon**: `destek/env_sablonu.env` dosyasını `.env` olarak kopyalayın
3. 🔑 Tüm API anahtarlarını `.env` dosyasına girin

### 4. ADIM: Uygulamayı Başlatın
```bash
python app.py server
```

### 5. ADIM: Test Edin
1. 🌐 http://localhost:5000 adresini ziyaret edin
2. 📱 API endpoints'lerini test edin
3. 👤 Admin kullanıcısı ile giriş yapın

## 📁 DESTEK DOSYALARI

### 🔧 Kurulum Rehberleri
- **`kurulum_sirasi.md`** ← Bu dosya (genel kurulum sırası)
- **`supabase_kurulum.md`** ← Supabase veritabanı kurulumu
- **`api_anahtarlari_rehberi.md`** ← API anahtarları ve servis bilgileri

### 📋 Yapılandırma Dosyaları
- **`env_sablonu.env`** ← .env dosyası şablonu
- **`replit_rehberi.md`** ← Proje mimarisi ve teknik detaylar

## ⚡ HIZLI BAŞLANGIÇ

Deneyimli geliştiriciler için hızlı kurulum:

```bash
# 1. .env dosyasını oluştur
cp destek/env_sablonu.env .env

# 2. API anahtarlarını .env'e ekle (manuel)
nano .env

# 3. Supabase SQL şemalarını çalıştır (Supabase dashboard'da)
# destek/supabase_kurulum.md dosyasındaki SQL kodları

# 4. Uygulamayı başlat
python app.py server
```

## 🔍 SORUN GİDERME

### Yaygın Hatalar:
1. **Supabase bağlantı hatası**: DATABASE_URL'i kontrol edin
2. **OpenAI API hatası**: API key ve kredi kontrolü yapın
3. **Redis bağlantı hatası**: Redis Cloud URL'ini kontrol edin
4. **Bunny.net yükleme hatası**: Storage zone ayarlarını kontrol edin

### Yardım Alın:
- 📖 İlgili rehber dosyalarını okuyun
- 📝 Log dosyalarını kontrol edin: `logs/app.log`
- 🔧 API servislerinin status sayfalarını kontrol edin

## 📞 DESTEK

Sorun yaşıyorsanız:
1. 🔍 İlk olarak `logs/error.log` dosyasını kontrol edin
2. 📚 İlgili rehber dosyasının sorun giderme bölümünü okuyun
3. 🔑 API anahtarlarının doğru ve güncel olduğunu kontrol edin
4. 🌐 Servis status sayfalarını kontrol edin

---

## 🎉 BAŞARILI KURULUM

Tüm adımları tamamladığınızda:
- ✅ API sunucusu http://localhost:5000 adresinde çalışır
- ✅ Kullanıcı kaydı ve girişi yapılabilir
- ✅ PDF belge yükleme sistemi çalışır
- ✅ Semantik arama yapılabilir
- ✅ Vektör embedding'ler Supabase'de saklanır

Başarılar! 🚀