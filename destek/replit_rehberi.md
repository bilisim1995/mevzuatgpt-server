# MevzuatGPT - Hukuki Belge RAG Sistemi

## Genel Bakış

MevzuatGPT, hukuki belge işleme ve semantik arama için tasarlanmış üretim kalitesinde bir RAG (Retrieval-Augmented Generation) sistemidir. Uygulama, admin kullanıcıların PDF belgeler yükleyebileceği ve kimlik doğrulaması yapılmış kullanıcıların doğal dil sorguları ile semantik aramalar yapabileceği rol tabanlı erişim kontrolü sağlar. Sistem, vektör benzerlik araması için OpenAI embeddings kullanır ve dosya depolama için Bunny.net CDN entegrasyonu içerir.

## Kullanıcı Tercihleri

Tercih edilen iletişim tarzı: Basit, günlük dil.

## Son Mimari Değişiklikler (7 Ağustos 2025)

### Büyük Güncellemeler - Supabase ve Redis Cloud Entegrasyonu
- **Supabase Auth**: Merkezi kullanıcı yönetimi için özel JWT kimlik doğrulaması Supabase Auth ile değiştirildi
- **Supabase Veritabanı**: Vektör işlemleri için birincil veritabanı olarak Supabase PostgreSQL'e geçiş yapıldı
- **Redis Cloud**: Celery yapılandırması yerel Redis yerine Redis Cloud kullanmak üzere güncellendi
- **RLS Güvenliği**: Güvenli veri erişimi için Satır Düzeyi Güvenlik politikaları uygulandı
- **Vektör Arama**: Benzerlik araması için optimize edilmiş `search_embeddings()` fonksiyonu oluşturuldu
- **API Modernizasyonu**: Tüm auth rotaları Supabase Auth servisi kullanmak üzere güncellendi
- **Bağımlılık Güncellemeleri**: FastAPI bağımlılıkları Supabase kimlik doğrulaması ile çalışmak üzere değiştirildi

### Gerekli Yapılandırma Güncellemeleri
- Tam işlevsellik için tüm harici servisler (OpenAI, Bunny.net, Supabase, Redis Cloud) artık zorunlu
- Kurulum rehberi için kapsamlı .env.example ve API_ANAHTARLARI_GEREKSINIMLERI.md eklendi
- Supabase kurulumu için tam SQL şeması ile models/supabase_models.py oluşturuldu

## Sistem Mimarisi

### Backend Framework
Uygulama, yüksek performans, otomatik OpenAPI dokümantasyon üretimi ve yerel Pydantic entegrasyonu için seçilen **FastAPI** web framework'ünü kullanır. FastAPI'nin asenkron yapısı, veritabanı işlemleri ve harici servis entegrasyonları ile uyumludur.

### Veritabanı Mimarisi
Sistem, vektör benzerlik araması için **pgvector** uzantısı ile birincil veritabanı olarak **Supabase PostgreSQL** kullanır. Veritabanı, güvenli veri erişimi için Satır Düzeyi Güvenlik (RLS) özelliği ve Supabase Auth ile sorunsuz kullanıcı yönetimi entegrasyonu sağlar.

Temel veritabanı tabloları:
- `auth.users` - Supabase yönetimli kullanıcı kimlik doğrulaması
- `public.user_profiles` - Genişletilmiş kullanıcı bilgileri ve roller
- `public.mevzuat_documents` - Belge metadata'sı ve dosya referansları
- `public.mevzuat_embeddings` - İçerik parçaları ile vektör embeddings
- `public.search_logs` - Analitik ve arama geçmişi

Veritabanı bağlantıları optimal performans için bağlantı havuzu ile yapılandırılmış SQLAlchemy async session'ları kullanır.

### Kimlik Doğrulama ve Yetkilendirme
**Supabase Auth**, **rol tabanlı erişim kontrolü (RBAC)** ile merkezi kimlik doğrulama ve kullanıcı yönetimi sağlar:
- `admin` - Belge yükleme ve yönetici işlevlerine erişim
- `user` - Belge arama ve erişimi

Kullanıcı kaydı, giriş ve oturum yönetimi Supabase'in Auth API'si aracılığıyla yapılır. JWT token'ları Supabase tarafından otomatik yenileme yetenekleri ve veritabanı erişim kontrolü için Satır Düzeyi Güvenlik (RLS) politikaları ile yönetilir.

### Dosya Depolama Stratejisi
**Bunny.net CDN**, maliyet etkinliği ve küresel dağıtım yetenekleri için seçilen PDF dosya depolama için kullanılır. Dosyalar, uygun hata işleme ve yeniden deneme mekanizmaları ile REST API aracılığıyla yüklenir.

### Arka Plan İşleme
**Redis Cloud ile Celery** aşağıdaki asenkron belge işleme görevlerini yönetir:
- PyPDF2 kullanarak PDF metin çıkarma
- LangChain'in RecursiveCharacterTextSplitter ile metin parçalama
- OpenAI embedding üretimi
- Supabase PostgreSQL'de vektör depolama

Redis Cloud, uzun belge işleme operasyonları sırasında ölçeklenebilir mesaj aracısı ve sonuç backend'i sağlayarak güvenilir görev dağıtımı ve uygulama engellenmesini önler.

### Yapılandırma Yönetimi
**Pydantic Settings**, ortam değişkenlerinden okuma ile tip doğrulamalı yapılandırma yönetimi, uygun varsayılanlar ve doğrulama sağlar. Bu, başlangıçta tüm gerekli yapılandırmaların mevcut ve düzgün tipte olmasını sağlar.

### Hata İşleme ve Loglama
Özel `AppException` sınıfları kullanan merkezi istisna işleme sistemi, uygun HTTP durum kodları ile yapılandırılmış hata yanıtları sağlar. Loglama, ortama göre rotasyon, çoklu formatlayıcılar ve farklı çıkış hedefleri (konsol, dosya) ile yapılandırılır.

### Vektör Arama Uygulaması
Semantik arama, 1536 boyutlu embeddings üretmek için **OpenAI'nin text-embedding-3-large** modelini kullanır. Bunlar **pgvector** uzantısı ile **Supabase PostgreSQL**'de depolanır. Benzerlik araması, belge parçaları arasında verimli sorgulama yapan özel `search_embeddings()` SQL fonksiyonu aracılığıyla yapılandırılabilir eşiklerle kosinüs mesafesi kullanır.

## Harici Bağımlılıklar

### AI Servisleri
- **OpenAI API** - Embedding üretimi (text-embedding-3-large) ve sohbet tamamlamaları (gpt-4o)

### Depolama Servisleri
- **Bunny.net Storage API** - PDF dosya depolama ve CDN dağıtımı

### Veritabanı Servisleri
- **Supabase PostgreSQL** - Embedding depolama ve Satır Düzeyi Güvenlik için pgvector uzantısı ile birincil veritabanı
- **Redis Cloud** - Celery arka plan görevleri ve önbellekleme için mesaj aracısı

### Kimlik Doğrulama ve Kullanıcı Yönetimi
- **Supabase Auth** - Eksiksiz kullanıcı kimlik doğrulaması, kayıt ve oturum yönetim sistemi

### Arka Plan İşleme
- **Celery** - Belge işleme için dağıtık görev kuyruğu
- **Redis Cloud** - Celery için mesaj aracısı ve sonuç backend'i

### Metin İşleme
- **LangChain** - Metin parçalama ve belge işleme yardımcı araçları
- **PyPDF2** - PDF metin çıkarma

### Python Kütüphaneleri
- **FastAPI** - Web framework ve API sunucusu
- **SQLAlchemy** - Async desteği ile veritabanı ORM
- **Pydantic** - Veri doğrulama ve ayar yönetimi
- **Alembic** - Veritabanı migrasyonları
- **Uvicorn** - Üretim dağıtımı için ASGI sunucusu

## Teknoloji Yığını Özeti

Bu projede kullanılan tüm teknolojiler:

✓ **Python (FastAPI)** - Ana backend framework
✓ **Supabase (PostgreSQL + Auth)** - Veritabanı ve kullanıcı yönetimi
✓ **Bunny.net** - Fiziksel dosya depolama ve CDN
✓ **LangChain** - Metin işleme ve parçalama
✓ **OpenAI** - Yapay zeka (vektörleştirme ve sohbet)
✓ **Celery** - Arka plan görev yöneticisi
✓ **Redis Cloud** - Celery için mesaj kuyruğu
✓ **Pydantic** - Veri doğrulama ve yapılandırma
✓ **SQLAlchemy** - Veritabanı etkileşimi
✓ **PyJWT** - Kimlik doğrulama token'ları (Supabase tarafından yönetilir)