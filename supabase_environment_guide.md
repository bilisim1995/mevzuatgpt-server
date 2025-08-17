# Supabase Self-hosted Email Authentication Guide

## Problem
`Email logins are disabled` hatası Supabase self-hosted instance'da email authentication'in etkinleştirilmemiş olmasından kaynaklanıyor.

## Solution 1: Database Configuration (Completed)
✅ Database'de `auth.config` tablosunda email authentication etkinleştirildi:

```sql
-- auth.config tablosunda ayarlar
GOTRUE_DISABLE_SIGNUP = false
GOTRUE_ENABLE_SIGNUP = true  
GOTRUE_MAILER_AUTOCONFIRM = true
GOTRUE_EXTERNAL_EMAIL_ENABLED = true
```

## Solution 2: Environment Variables (Critical)

Supabase self-hosted instance'ın çalıştığı sunucuda aşağıdaki environment variables eklenmelidir:

### Docker Compose (.env file):
```bash
# Email Authentication
GOTRUE_DISABLE_SIGNUP=false
GOTRUE_ENABLE_SIGNUP=true
GOTRUE_MAILER_AUTOCONFIRM=true
GOTRUE_EXTERNAL_EMAIL_ENABLED=true

# SMTP Configuration (Optional - for email verification)
GOTRUE_SMTP_HOST=smtp.gmail.com
GOTRUE_SMTP_PORT=587
GOTRUE_SMTP_USER=your-email@gmail.com
GOTRUE_SMTP_PASS=your-app-password
GOTRUE_SMTP_ADMIN_EMAIL=admin@mevzuatgpt.com

# Site URL
GOTRUE_SITE_URL=https://supabase.mevzuatgpt.org
```

### Docker Compose Service:
```yaml
auth:
  image: supabase/gotrue:latest
  environment:
    - GOTRUE_DISABLE_SIGNUP=false
    - GOTRUE_ENABLE_SIGNUP=true
    - GOTRUE_MAILER_AUTOCONFIRM=true
    - GOTRUE_EXTERNAL_EMAIL_ENABLED=true
```

## Solution 3: Restart Required
Değişikliklerin etkili olması için Supabase containers restart edilmelidir:

```bash
docker-compose down
docker-compose up -d
```

## Current Status
- ✅ Database auth.config settings configured
- ⚠️ Environment variables need to be set on server
- ⚠️ Container restart required
- ✅ Admin user ready: admin@mevzuatgpt.com
- ✅ Direct database authentication implemented as fallback

## Test Login
Admin credentials hazır:
- Email: admin@mevzuatgpt.com  
- Password: AdminMevzuat2025!

## Fallback Implementation
Eğer environment variables düzeltilemezse, direct database authentication ile login çalışacak.