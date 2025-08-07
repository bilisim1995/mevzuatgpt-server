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

## Gereksinimler

Environment variables:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`