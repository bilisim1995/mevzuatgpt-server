# MevzuatGPT Test Utilities

Bu klasör MevzuatGPT için test araçlarını içerir.

## Kullanıcı Oluşturma Araçları

### Admin Kullanıcı Oluşturma
```bash
python tests/create_admin_user.py
```
- Rastgele admin kullanıcısı oluşturur
- Email, şifre ve diğer bilgileri otomatik üretir
- Login testi yapar

### Normal Kullanıcı Oluşturma
```bash
python tests/create_user.py
```
- Rastgele normal kullanıcı oluşturur
- Türkçe isimler kullanır
- Login testi yapar

## Özellikler

### Admin Kullanıcı
- **Role:** `admin`
- **Yetkiler:** PDF yükleme, tüm admin işlevleri
- **Email formatı:** `admin123@mevzuatgpt.com`

### Normal Kullanıcı
- **Role:** `user`
- **Yetkiler:** Arama, belge erişimi
- **Email formatı:** `ahmet.yilmaz123@example.com`

## Güvenlik

- Şifreler rastgele üretilir (12+ karakter)
- Özel karakterler içerir
- Her çalıştırmada farklı kullanıcı oluşturulur

### Bunny.net Storage Test
```bash
python tests/test_bunny_storage.py
```
- Bunny.net bağlantısını test eder
- Test dosyası upload/delete işlemlerini doğrular
- Environment variables kontrolü yapar

## Gereksinimler

### Kullanıcı Oluşturma
Environment variables:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

### Storage Test
Environment variables:
- `BUNNY_STORAGE_API_KEY`
- `BUNNY_STORAGE_ZONE`
- `BUNNY_STORAGE_REGION`
- `BUNNY_STORAGE_ENDPOINT`

### Redis Connection Test
```bash
python tests/test_redis_connection.py
```
- Redis Cloud bağlantısını test eder
- Temel Redis operasyonlarını doğrular
- Celery broker/backend bağlantılarını test eder
- Redis sunucu bilgilerini gösterir

Environment variables:
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`