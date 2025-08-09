# 🏛️ MevzuatGPT - Hukuki Belge RAG Sistemi

> Yapay zeka destekli hukuki belge arama ve analiz platformu

## 🎯 Proje Hakkında

MevzuatGPT, hukuk firmalarına ve kamu kurumlarına yönelik geliştirilmiş modern bir RAG (Retrieval-Augmented Generation) sistemidir. PDF formatındaki hukuki belgeleri analiz ederek, doğal dil ile akıllı arama imkanı sunar.

### ✨ Temel Özellikler

- 🔐 **Güvenli Kullanıcı Yönetimi** - Supabase Auth ile rol tabanlı erişim
- 📄 **PDF Belge İşleme** - Otomatik metin çıkarma ve vektörizasyon
- 🔍 **Semantik Arama** - OpenAI embeddings ile anlam tabanlı arama
- ⚡ **Yüksek Performans** - FastAPI ve PostgreSQL vector search
- 📊 **Yönetim Paneli** - Admin kullanıcılar için kapsamlı kontrol
- 🌐 **CDN Entegrasyonu** - Bunny.net ile hızlı dosya erişimi

### 🛠️ Teknoloji Yığını

- **Backend**: Python (FastAPI)
- **Veritabanı**: Supabase PostgreSQL + pgvector
- **Auth**: Supabase Authentication
- **AI**: OpenAI (text-embedding-3-large, gpt-4o)
- **Storage**: Bunny.net CDN
- **Background Tasks**: Celery + Redis Cloud
- **Text Processing**: LangChain

## 🚀 Hızlı Başlangıç

### Önkoşullar

Aşağıdaki servislere kaydolmanız gerekir:
- [OpenAI API](https://platform.openai.com/)
- [Supabase](https://app.supabase.com/)
- [Bunny.net](https://panel.bunny.net/)
- [Redis Cloud](https://app.redislabs.com/)

### Kurulum

1. **Proje dosyalarını indirin**
```bash
git clone <repository-url>
cd mevzuatgpt
```

2. **Kurulum rehberini takip edin**
```bash
# Detaylı kurulum için:
cat destek/kurulum_sirasi.md
```

3. **Hızlı başlangıç**
```bash
# .env dosyasını oluşturun
cp destek/env_sablonu.env .env

# API anahtarlarını .env dosyasına ekleyin
nano .env

# Supabase veritabanını kurun (destek/supabase_kurulum.md)
# SQL kodlarını Supabase dashboard'da çalıştırın

# Uygulamayı başlatın
python app.py server
```

## 📚 Dökümantasyon

Tüm kurulum ve kullanım rehberleri `destek/` klasöründe bulunur:

### 🔧 Kurulum Rehberleri
- **[Kurulum Sırası](destek/kurulum_sirasi.md)** - Adım adım kurulum rehberi
- **[Supabase Kurulum](destek/supabase_kurulum.md)** - Veritabanı ve auth kurulumu
- **[API Anahtarları](destek/api_anahtarlari_rehberi.md)** - Gerekli servis bilgileri

### 📖 Teknik Dökümantasyon
- **[Proje Mimarisi](destek/replit_rehberi.md)** - Teknik detaylar ve mimari
- **[Yapılandırma Şablonu](destek/env_sablonu.env)** - Ortam değişkenleri

## 🏗️ Mimari

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   Supabase      │
│   (Web/Mobile)  │───▶│   Backend       │───▶│   PostgreSQL    │
│                 │    │                 │    │   + pgvector    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │   Celery        │    │   OpenAI        │
                    │   + Redis       │───▶│   Embeddings    │
                    │   Background    │    │   + ChatGPT     │
                    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌─────────────────┐
                    │   Bunny.net     │
                    │   CDN Storage   │
                    │                 │
                    └─────────────────┘
```

## 🔧 Geliştirme

### Yerel Geliştirme Ortamı

```bash
# Geliştirme sunucusunu başlatın
python app.py server

# Celery worker'ı başlatın (ayrı terminal)
celery -A tasks.celery_app worker --loglevel=info

# Log dosyalarını takip edin
tail -f logs/app.log
```

### API Endpoints

- **Auth**: `/api/auth/` - Kullanıcı girişi, kaydı
- **Admin**: `/api/admin/` - Belge yönetimi
- **User**: `/api/user/` - Arama ve kullanıcı işlemleri
- **Docs**: `/docs` - Otomatik API dökümantasyonu

## 🔐 Güvenlik

- ✅ JWT tabanlı kimlik doğrulama
- ✅ Role-based access control (RBAC)
- ✅ Row Level Security (RLS) in database
- ✅ API rate limiting
- ✅ Input validation ve sanitization

## 📊 Performans

- ⚡ Async FastAPI with connection pooling
- 🚀 Vector similarity search with pgvector
- 📈 CDN caching for file delivery
- 🔄 Background processing with Celery
- 📊 Optimized database indexing

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 💬 İletişim

- 📧 Email: [email@example.com]
- 🐛 Issues: [GitHub Issues](link-to-issues)
- 📚 Wiki: [Project Wiki](link-to-wiki)

## 🙏 Teşekkürler

Bu proje aşağıdaki açık kaynak projelerini kullanır:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Supabase](https://supabase.com/)
- [OpenAI](https://openai.com/)
- [LangChain](https://langchain.com/)
- [Celery](https://celery.dev/)

---

**MevzuatGPT** - Hukuki belgelerinizi akıllı arama ile keşfedin 🚀