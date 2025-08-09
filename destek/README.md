# MevzuatGPT Destek Ticket Sistemi

## 📋 Genel Bakış

Bu modül, kullanıcıların sistem ile ilgili sorunlarını rapor edebilmeleri, soru sorabilmeleri ve geri bildirimde bulunabilmeleri için geliştirilmiş bir destek ticket sistemidir. Sistem tamamen modüler olarak tasarlanmış olup mevcut MevzuatGPT altyapısını etkilemeden çalışır.

## 🏗️ Sistem Mimarisi

### Veritabanı Yapısı

#### support_tickets tablosu
- **id**: UUID birincil anahtar
- **ticket_number**: Otomatik oluşturulan ticket numarası (TK-001 formatında)
- **user_id**: Ticket oluşturan kullanıcının UUID'si
- **subject**: Ticket konusu (maksimum 200 karakter)
- **category**: Ticket kategorisi
- **priority**: Ticket öncelik seviyesi
- **status**: Ticket durumu
- **created_at**: Oluşturulma tarihi
- **updated_at**: Son güncelleme tarihi

#### support_messages tablosu
- **id**: UUID birincil anahtar
- **ticket_id**: Hangi ticket'a ait olduğu
- **sender_id**: Mesajı gönderen kullanıcının UUID'si
- **message**: Mesaj içeriği
- **created_at**: Mesaj gönderme tarihi

### Kategoriler
- `teknik_sorun`: PDF yükleme, sistem hataları, performans sorunları
- `hesap_sorunu`: Login sorunları, kredi sorunları, profil ayarları
- `ozellik_talebi`: Yeni özellik istekleri, geliştirme önerileri
- `guvenlik`: Güvenlik endişeleri, şüpheli aktiviteler
- `faturalandirma`: Ödeme sorunları, fatura soruları
- `genel_soru`: Genel kullanım soruları, rehberlik
- `diger`: Diğer konular

### Öncelik Seviyeleri
- `dusuk`: Genel sorular, özellik talepleri
- `orta`: Standart teknik sorunlar
- `yuksek`: Kritik işlevsellik sorunları
- `acil`: Güvenlik sorunları, sistem erişim sorunları

### Durum Seviyeleri
- `acik`: Yeni oluşturulan veya kullanıcı yanıtı bekleyen
- `cevaplandi`: Admin tarafından yanıtlanmış
- `kapatildi`: Çözüme ulaşmış veya manuel olarak kapatılmış

## 🔐 Güvenlik ve Yetkilendirme

### RLS Politikaları
- **Kullanıcılar**: Sadece kendi ticket'larını görebilir ve yönetebilir
- **Adminler**: Tüm ticket'ları görebilir ve yönetebilir
- **Service Role**: Backend işlemler için tam erişim

### Yetki Kontrolü
- JWT token doğrulama
- User role kontrolü (admin/user)
- Ticket sahiplik kontrolü

## 📡 API Endpoint'leri

### Kullanıcı Endpoint'leri (`/api/user/support`)
- `POST /tickets` - Yeni ticket oluştur
- `GET /tickets` - Kendi ticket'larını listele
- `GET /tickets/{id}` - Ticket detay ve mesajlar
- `POST /tickets/{id}/reply` - Ticket'a mesaj ekle

### Admin Endpoint'leri (`/api/admin/support`)
- `GET /tickets` - Tüm ticket'ları listele (filtreleme destekli)
- `GET /tickets/{id}` - Herhangi bir ticket detayı
- `POST /tickets/{id}/reply` - Admin yanıtı ekle
- `PUT /tickets/{id}/status` - Ticket durumu güncelle

## 🔧 Dosya Yapısı

```
destek/
├── README.md                    # Bu dosya
├── supabase_migration.sql       # Veritabanı migration
models/
├── support_schemas.py           # Pydantic modelleri
services/
├── support_service.py           # İş mantığı servisi
api/
├── user/
│   └── support_routes.py        # Kullanıcı API endpoint'leri
└── admin/
    └── support_routes.py        # Admin API endpoint'leri
```

## 🎯 Özellikler

### Temel İşlevsellik
- ✅ Ticket oluşturma ve yönetimi
- ✅ Mesaj bazlı iletişim
- ✅ Otomatik ticket numarası oluşturma
- ✅ Kategori ve öncelik sistemi
- ✅ Durum takibi

### Gelişmiş Özellikler
- ✅ Pagination desteği
- ✅ Filtreleme ve arama
- ✅ Admin yönetim paneli
- ✅ RLS tabanlı güvenlik
- ✅ Modüler tasarım

## 🚀 Kurulum ve Kullanım

### 1. Veritabanı Kurulumu
```bash
# Supabase SQL Editor'da çalıştır
cat destek/supabase_migration.sql
```

### 2. API Entegrasyonu
Sistem otomatik olarak mevcut FastAPI uygulamasına entegre edilir.

### 3. Test
Postman collection'ı ile API endpoint'lerini test edebilirsiniz.

## 📊 Performans Notları

- PostgreSQL indeksleri ile optimize edilmiş sorgular
- RLS ile güvenli veri erişimi
- Pagination ile büyük veri setleri desteği
- Async/await ile yüksek performans

## 🔄 Genişletme İmkanları

- Email bildirimleri entegrasyonu
- Dosya eklentisi desteği
- Ticket otomatik atama
- SLA takip sistemi
- Dashboard ve raporlama

---

**Not**: Bu sistem tamamen modüler olarak tasarlanmıştır ve mevcut MevzuatGPT işlevselliğini etkilemez.