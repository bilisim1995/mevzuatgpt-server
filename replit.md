# MevzuatGPT - Hukuki Belge RAG Sistemi

## Genel Bakış

MevzuatGPT, hukuki belge işleme ve semantik arama için tasarlanmış üretim kalitesinde bir RAG (Retrieval-Augmented Generation) sistemidir. Admin kullanıcıların PDF belgeler yükleyebileceği ve kimlik doğrulaması yapılmış kullanıcıların doğal dil sorguları ile semantik aramalar yapabileceği rol tabanlı erişim kontrolü sağlar. Sistem, vektör benzerlik araması için OpenAI embeddings kullanır ve dosya depolama için Bunny.net CDN entegrasyonu içerir.

## Kullanıcı Tercihleri

Tercih edilen iletişim tarzı: Basit, günlük dil. Türkçe iletişim.

## Son Mimari Değişiklikler (8 Ağustos 2025)

### PDF Processing Pipeline Tamamen Operasyonel ✅
- **Database**: Neon PostgreSQL kullanılıyor (pgvector aktif, 3072 dimension)
- **Embedding Storage**: String parsing sorunu çözüldü, vektörler doğru formatta kaydediliyor
- **Async Loop Management**: Celery task'larda connection cleanup sistemi eklendi
- **OpenAI API**: 100% operasyonel (embedding + chat), quota sorunu çözüldü
- **Queue Management**: Redis Cloud bağlantısı stabil, worker health monitoring aktif
- **Error Handling**: Kapsamlı retry logic ve status tracking sistemi

### Veritabanı Durumu
- **Neon Database**: db.omublqdeerbszkuuvoim.supabase.co yerine ep-soft-credit-afgz97nh.c-2.us-west-2.aws.neon.tech kullanılıyor
- **Tablolar**: mevzuat_documents (2 kayıt), mevzuat_embeddings (pgvector hazır)
- **Admin Panel**: Neon Console üzerinden tabloları görüntüleyebilirsiniz

## Son Mimari Değişiklikler (7 Ağustos 2025)

### Büyük Güncellemeler - Supabase ve Redis Cloud Entegrasyonu
- **Supabase Auth**: Merkezi kullanıcı yönetimi için özel JWT kimlik doğrulaması Supabase Auth ile değiştirildi
- **Supabase Veritabanı**: Vektör işlemleri için birincil veritabanı olarak Supabase PostgreSQL'e geçiş yapıldı
- **Redis Cloud**: Celery yapılandırması yerel Redis yerine Redis Cloud kullanmak üzere güncellendi
- **RLS Güvenliği**: Güvenli veri erişimi için Satır Düzeyi Güvenlik politikaları uygulandı
- **Vektör Arama**: Benzerlik araması için optimize edilmiş `search_embeddings()` fonksiyonu oluşturuldu
- **API Modernizasyonu**: Tüm auth rotaları Supabase Auth servisi kullanmak üzere güncellendi
- **Bağımlılık Güncellemeleri**: FastAPI bağımlılıkları Supabase kimlik doğrulaması ile çalışmak üzere değiştirildi
- **Dökümantasyon**: Tüm kurulum rehberleri Türkçeleştirildi ve destek/ klasöründe toplandı

### Dökümantasyon Organizasyonu
- Tüm kurulum ve yapılandırma dosyaları `destek/` klasörüne taşındı
- Türkçe rehberler oluşturuldu: kurulum_sirasi.md, supabase_kurulum.md, api_anahtarlari_rehberi.md
- API kullanım rehberleri: endpoints.md, postman_rehberi.md, pdf_upload_rehberi.md
- Ana README.md dosyası projeye genel bakış için güncellendi

## Sistem Mimarisi

### Backend Framework
Uygulama, yüksek performans, otomatik OpenAPI dokümantasyon üretimi ve yerel Pydantic entegrasyonu için seçilen **FastAPI** web framework'ünü kullanır.

### Veritabanı Mimarisi
Sistem, vektör benzerlik araması için **pgvector** uzantısı ile birincil veritabanı olarak **Supabase PostgreSQL** kullanır. Veritabanı, güvenli veri erişimi için Satır Düzeyi Güvenlik (RLS) özelliği ve Supabase Auth ile sorunsuz kullanıcı yönetimi entegrasyonu sağlar.

### Kimlik Doğrulama ve Yetkilendirme
**Supabase Auth**, **rol tabanlı erişim kontrolü (RBAC)** ile merkezi kimlik doğrulama ve kullanıcı yönetimi sağlar:
- `admin` - Belge yükleme ve yönetici işlevlerine erişim
- `user` - Belge arama ve erişimi

### Dosya Depolama Stratejisi
**Bunny.net CDN**, maliyet etkinliği ve küresel dağıtım yetenekleri için seçilen PDF dosya depolama için kullanılır.

### Arka Plan İşleme
**Redis Cloud ile Celery** asenkron belge işleme görevlerini yönetir:
- PDF metin çıkarma, metin parçalama, OpenAI embedding üretimi, vektör depolama

### Vektör Arama Uygulaması
Semantik arama, **OpenAI'nin text-embedding-3-large** modelini kullanarak 1536 boyutlu embeddings üretir. Bunlar **Supabase PostgreSQL**'de **pgvector** uzantısı ile depolanır.

## Harici Bağımlılıklar

### Zorunlu Servisler
- **OpenAI API** - Embedding üretimi ve ChatGPT
- **Supabase** - Veritabanı, auth ve vektör işlemleri
- **Bunny.net** - PDF dosya depolama ve CDN
- **Redis Cloud** - Celery background tasks

### Python Kütüphaneleri
- **FastAPI** - Web framework
- **SQLAlchemy** - Async veritabanı ORM
- **Pydantic** - Veri doğrulama
- **LangChain** - Metin işleme
- **Celery** - Background tasks
- **Supabase Python Client** - Supabase entegrasyonu

## Teknoloji Yığını

✓ **Python (FastAPI)** - Ana backend framework
✓ **Supabase (PostgreSQL + Auth)** - Veritabanı ve kullanıcı yönetimi
✓ **Bunny.net** - Fiziksel dosya depolama ve CDN
✓ **LangChain** - Metin işleme ve parçalama
✓ **OpenAI** - Yapay zeka (vektörleştirme ve sohbet)
✓ **Celery** - Arka plan görev yöneticisi
✓ **Redis Cloud** - Celery için mesaj kuyruğu
✓ **Pydantic** - Veri doğrulama ve yapılandırma
✓ **SQLAlchemy** - Veritabanı etkileşimi
✓ **PyJWT** - Kimlik doğrulama (Supabase yönetimli)