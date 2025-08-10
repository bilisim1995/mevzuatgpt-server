# RLS Policy Düzeltme Rehberi

## 🚨 Sorun
Supabase'de `infinite recursion detected in policy` hatası alıyorsun. Bu RLS policy'lerinde döngüsel bağımlılık olduğu anlamına geliyor.

## 🔧 Çözüm Adımları

### 1. Supabase Dashboard'a Git
- [Supabase Dashboard](https://supabase.com/dashboard) 
- Projen → SQL Editor

### 2. SQL Kodunu Çalıştır
`fix_rls_policies.sql` dosyasındaki tüm SQL kodunu Supabase SQL Editor'da çalıştır.

### 3. Adım Adım Kontrol

**Adım 1:** Eski policy'leri sil
```sql
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
-- ... (dosyadaki tüm DROP komutları)
```

**Adım 2:** Yeni policy'leri oluştur
```sql
CREATE POLICY "Enable read access for users"
ON user_profiles FOR SELECT
USING (auth.uid()::text = id::text);
-- ... (dosyadaki tüm CREATE komutları)
```

**Adım 3:** İzinleri ayarla
```sql
GRANT ALL ON user_profiles TO authenticated;
-- ... (dosyadaki tüm GRANT komutları)
```

### 4. Test Et
SQL Editor'da şu komutu çalıştırarak kontrol et:
```sql
SELECT schemaname, tablename, policyname 
FROM pg_policies 
WHERE tablename IN ('user_profiles', 'support_tickets', 'support_messages');
```

## 📋 Beklenen Sonuç

Komutları çalıştırdıktan sonra:
- ✅ RLS infinite recursion hatası kalkar
- ✅ Support ticket'lar çalışır
- ✅ Admin ve kullanıcı erişimleri düzgün çalışır

## 🧪 Sistem Testi

SQL'leri çalıştırdıktan sonra şu endpoint'leri test edebiliriz:
- `GET /api/user/tickets` - Kullanıcı ticket'ları
- `POST /api/user/tickets` - Yeni ticket oluştur  
- `GET /api/admin/tickets` - Admin tüm ticket'ları

## ⚠️ Önemli Notlar

1. **Service Role**: API sunucumuz service_role anahtarı kullanıyor, bu yüzden RLS bypass edilir.
2. **Authenticated Role**: Kullanıcı JWT token'ları authenticated role kullanır.
3. **Policy Sırası**: Policy'ler sırayla değerlendirilir, ilk eşleşen kullanılır.

## 🔍 Sorun Devam Ederse

Eğer hala hata alırsan:
1. Supabase logs'ları kontrol et
2. `fix_rls_policies.sql` dosyasını tekrar çalıştır
3. Table Editor'da RLS'nin açık olduğunu doğrula