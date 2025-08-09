-- ===================================================================
-- KULLANICI PROFİL GENİŞLETME - SUPABASE MIGRATION
-- Bu SQL kodlarını Supabase SQL Editor'da çalıştırın
-- ===================================================================

-- 1. user_profiles tablosuna yeni kolonlar ekle
ALTER TABLE public.user_profiles 
ADD COLUMN IF NOT EXISTS ad VARCHAR(50),
ADD COLUMN IF NOT EXISTS soyad VARCHAR(50), 
ADD COLUMN IF NOT EXISTS meslek VARCHAR(100),
ADD COLUMN IF NOT EXISTS calistigi_yer VARCHAR(150);

-- 2. Yeni kolonlar için yorum ekle
COMMENT ON COLUMN public.user_profiles.ad IS 'Kullanıcının adı (opsiyonel)';
COMMENT ON COLUMN public.user_profiles.soyad IS 'Kullanıcının soyadı (opsiyonel)';
COMMENT ON COLUMN public.user_profiles.meslek IS 'Kullanıcının mesleği (opsiyonel)';
COMMENT ON COLUMN public.user_profiles.calistigi_yer IS 'Kullanıcının çalıştığı yer (opsiyonel)';

-- 3. Yeni indeksler oluştur (arama performansı için)
CREATE INDEX IF NOT EXISTS idx_user_profiles_ad ON public.user_profiles(ad);
CREATE INDEX IF NOT EXISTS idx_user_profiles_soyad ON public.user_profiles(soyad);  
CREATE INDEX IF NOT EXISTS idx_user_profiles_meslek ON public.user_profiles(meslek);
CREATE INDEX IF NOT EXISTS idx_user_profiles_calistigi_yer ON public.user_profiles(calistigi_yer);

-- 4. Composite index (tam isim arama için)
CREATE INDEX IF NOT EXISTS idx_user_profiles_full_name_components 
ON public.user_profiles(ad, soyad);

-- ===================================================================
-- DOĞRULAMA SORGULARI
-- ===================================================================

-- 1. Yeni kolonlar eklendi mi?
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'user_profiles'
AND column_name IN ('ad', 'soyad', 'meslek', 'calistigi_yer')
ORDER BY column_name;

-- 2. İndeksler oluşturuldu mu?
SELECT indexname, indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename = 'user_profiles'
AND indexname LIKE 'idx_user_profiles_%'
ORDER BY indexname;

-- 3. Tablo yapısı kontrol
\d+ public.user_profiles;

-- ===================================================================
-- ÖRNEK KULLANIM (Test amaçlı)
-- ===================================================================

-- Profil güncelleme örneği (giriş yapmış kullanıcı için):
/*
UPDATE public.user_profiles 
SET 
    ad = 'Ahmet',
    soyad = 'Yılmaz', 
    meslek = 'Avukat',
    calistigi_yer = 'İstanbul Adalet Sarayı',
    updated_at = NOW()
WHERE id = auth.uid();
*/

-- Profil bilgilerini görüntüleme:
/*
SELECT 
    email,
    full_name,
    ad,
    soyad,
    meslek,
    calistigi_yer,
    role,
    created_at
FROM public.user_profiles 
WHERE id = auth.uid();
*/

-- ===================================================================
-- BAŞARILI MIGRATION KONTROLÜ
-- ===================================================================

-- Bu sorgu başarılı çalışırsa migration tamamdır:
SELECT 
    'User Profile Migration Başarılı!' as status,
    COUNT(*) as total_users,
    COUNT(ad) as users_with_name,
    COUNT(meslek) as users_with_profession
FROM public.user_profiles;

-- ===================================================================
-- SON NOT: 
-- Bu migration'dan sonra kullanıcı kayıt sistemi genişletilmiş 
-- profil bilgilerini kabul edecektir.
-- ===================================================================