# 🚀 Supabase Kurulum ve Yapılandırma Rehberi

Bu rehber, MevzuatGPT uygulaması için Supabase'in nasıl kurulacağını ve yapılandırılacağını adım adım açıklar.

## 📋 Gereksinimler

- Supabase hesabı (ücretsiz): https://app.supabase.com/
- PostgreSQL pgvector extension desteği
- Row Level Security (RLS) aktifleştirme yetkisi

## 🎯 Adım 1: Supabase Projesi Oluşturma

### 1.1 Yeni Proje Oluşturun
1. https://app.supabase.com/ adresine gidin
2. "New Project" butonuna tıklayın
3. Proje bilgilerini doldurun:
   - **Name**: `MevzuatGPT`
   - **Organization**: Mevcut organizasyonunuzu seçin
   - **Region**: `Europe (Central)` - en yakın bölge
   - **Database Password**: Güçlü bir şifre oluşturun (kaydedin!)

### 1.2 Proje Bilgilerini Kopyalayın
Proje oluşturulduktan sonra:
1. **Settings** > **API** sayfasına gidin
2. Aşağıdaki bilgileri kopyalayın:
   - **Project URL**: `https://xxxxxxxxx.supabase.co`
   - **anon/public key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - **service_role key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

### 1.3 Database Connection String
1. **Settings** > **Database** sayfasına gidin
2. **Connection string** > **URI** bölümünden connection string'i kopyalayın
3. `[YOUR-PASSWORD]` kısmını gerçek şifrenizle değiştirin

## 🎯 Adım 2: Vector Extension Etkinleştirme

### 2.1 SQL Editor'u Açın
1. Supabase dashboard'da **SQL Editor** sekmesine gidin
2. Yeni bir query oluşturun

### 2.2 Vector Extension'ını Aktifleştirin
```sql
-- Vector extension'ını etkinleştir
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

Bu kodu çalıştırın. Başarılı olursa "Success. No rows returned" mesajı göreceksiniz.

## 🎯 Adım 3: Ana Veritabanı Şeması Oluşturma

### 3.1 Tablo Şemalarını Oluşturun
Aşağıdaki SQL kodunu SQL Editor'da çalıştırın:

```sql
-- ============================================================
-- KULLANICI PROFİLLERİ TABLOSU
-- ============================================================
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    full_name TEXT,
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- MEVZUAT BELGELERİ TABLOSU
-- ============================================================
CREATE TABLE IF NOT EXISTS public.mevzuat_documents (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_size BIGINT,
    content_preview TEXT,
    upload_date TIMESTAMPTZ DEFAULT NOW(),
    uploaded_by UUID REFERENCES auth.users(id),
    status TEXT DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- VEKTÖR EMBEDDINGS TABLOSU
-- ============================================================
CREATE TABLE IF NOT EXISTS public.mevzuat_embeddings (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    document_id UUID REFERENCES public.mevzuat_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536), -- OpenAI text-embedding-3-large boyutu
    chunk_index INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ARAMA LOGLAR TABLOSU
-- ============================================================
CREATE TABLE IF NOT EXISTS public.search_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    query TEXT NOT NULL,
    results_count INTEGER,
    execution_time FLOAT,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 🎯 Adım 4: Row Level Security (RLS) Politikaları

### 4.1 RLS'yi Etkinleştirin
```sql
-- Tüm tablolar için RLS'yi etkinleştir
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mevzuat_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mevzuat_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.search_logs ENABLE ROW LEVEL SECURITY;
```

### 4.2 Güvenlik Politikalarını Oluşturun
```sql
-- ============================================================
-- USER PROFILES POLİTİKALARI
-- ============================================================
CREATE POLICY "Kullanıcılar kendi profilini görebilir" ON public.user_profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Kullanıcılar kendi profilini güncelleyebilir" ON public.user_profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Adminler tüm profilleri görebilir" ON public.user_profiles
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- ============================================================
-- DOCUMENTS POLİTİKALARI
-- ============================================================
CREATE POLICY "Herkes tamamlanmış belgeleri görebilir" ON public.mevzuat_documents
    FOR SELECT USING (status = 'completed');

CREATE POLICY "Adminler tüm belgeleri yönetebilir" ON public.mevzuat_documents
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- ============================================================
-- EMBEDDINGS POLİTİKALARI
-- ============================================================
CREATE POLICY "Herkes embeddings'lerde arama yapabilir" ON public.mevzuat_embeddings
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.mevzuat_documents 
            WHERE id = document_id AND status = 'completed'
        )
    );

CREATE POLICY "Adminler embeddings'leri yönetebilir" ON public.mevzuat_embeddings
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- ============================================================
-- SEARCH LOGS POLİTİKALARI
-- ============================================================
CREATE POLICY "Kullanıcılar kendi arama geçmişini görebilir" ON public.search_logs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Herkes arama logu ekleyebilir" ON public.search_logs
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Adminler tüm arama loglarını görebilir" ON public.search_logs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );
```

## 🎯 Adım 5: Vektör Arama Fonksiyonu

### 5.1 Ana Arama Fonksiyonunu Oluşturun
```sql
-- ============================================================
-- VEKTÖR ARAMA FONKSİYONU
-- ============================================================
CREATE OR REPLACE FUNCTION search_embeddings(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    content text,
    similarity float,
    document_title text,
    document_filename text
)
LANGUAGE sql STABLE
AS $$
    SELECT 
        e.id,
        e.document_id,
        e.content,
        1 - (e.embedding <=> query_embedding) AS similarity,
        d.title AS document_title,
        d.filename AS document_filename
    FROM mevzuat_embeddings e
    JOIN mevzuat_documents d ON e.document_id = d.id
    WHERE 
        d.status = 'completed'
        AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
$$;
```

## 🎯 Adım 6: Otomatik Trigger'lar ve Fonksiyonlar

### 6.1 Kullanıcı Profili Otomatik Oluşturma
```sql
-- ============================================================
-- YENİ KULLANICI KAYDINDAN SONRA PROFİL OLUŞTURMA
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.user_profiles (id, full_name, role)
    VALUES (
        new.id, 
        COALESCE(new.raw_user_meta_data->>'full_name', new.email),
        COALESCE(new.raw_user_meta_data->>'role', 'user')
    );
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger'ı oluştur
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
```

### 6.2 Otomatik Zaman Damgası Güncellemesi
```sql
-- ============================================================
-- OTOMATIK UPDATED_AT GÜNCELLEMESİ
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger'ları uygula
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON public.mevzuat_documents
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
```

## 🎯 Adım 7: Performans İndeksleri

### 7.1 Önemli İndeksleri Oluşturun
```sql
-- ============================================================
-- PERFORMANS İNDEKSLERİ
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON public.mevzuat_embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON public.mevzuat_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.mevzuat_documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON public.mevzuat_documents(upload_date);
CREATE INDEX IF NOT EXISTS idx_search_logs_user_id ON public.search_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON public.search_logs(created_at);
```

## 🎯 Adım 8: İlk Admin Kullanıcı Oluşturma

### 8.1 Supabase Auth Panel'den
1. **Authentication** > **Users** sayfasına gidin
2. **Add user** butonuna tıklayın
3. Admin kullanıcı bilgilerini girin:
   - **Email**: admin@example.com
   - **Password**: Güçlü bir şifre
   - **Auto Confirm User**: ✅ işaretleyin

### 8.2 Admin Rolü Atama
Kullanıcı oluşturulduktan sonra SQL Editor'da:
```sql
-- İlk admin kullanıcısına admin rolü ver
UPDATE public.user_profiles 
SET role = 'admin' 
WHERE id = (
    SELECT id FROM auth.users 
    WHERE email = 'admin@example.com'
);
```

## 🎯 Adım 9: Test ve Doğrulama

### 9.1 Tabloları Kontrol Edin
```sql
-- Tabloların oluştuğunu kontrol et
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';
```

### 9.2 RLS Politikalarını Kontrol Edin
```sql
-- RLS politikalarını kontrol et
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies 
WHERE schemaname = 'public';
```

### 9.3 Vector Extension'ını Kontrol Edin
```sql
-- Vector extension'ının yüklü olduğunu kontrol et
SELECT * FROM pg_extension WHERE extname = 'vector';
```

## 🎯 Adım 10: .env Dosyasını Güncelleyin

Supabase bilgilerinizi .env dosyasına ekleyin:
```bash
# Supabase Ayarları
SUPABASE_URL=https://xxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres.xxxxxxxxx:password@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
```

## ✅ Tamamlandı!

Supabase kurulumunuz tamamlandı! Artık MevzuatGPT uygulaması:
- ✅ Kullanıcı kimlik doğrulaması yapabilir
- ✅ Belge metadata'sını saklayabilir
- ✅ Vektör embeddings'leri depolayabilir
- ✅ Semantik arama yapabilir
- ✅ Güvenli veri erişimi sağlayabilir

## 🔧 Sorun Giderme

### Yaygın Hatalar:
1. **Vector extension bulunamıyor**: Supabase projesinin vector desteği olduğundan emin olun
2. **RLS hataları**: Service role key'in doğru olduğunu kontrol edin
3. **Bağlantı hataları**: Database URL'in doğru ve şifrenin güncel olduğunu kontrol edin
4. **Trigger hataları**: SECURITY DEFINER yetkilerinin doğru olduğunu kontrol edin

### Yardım:
- Supabase dokümantasyonu: https://supabase.com/docs
- Vector extension rehberi: https://supabase.com/docs/guides/database/extensions/pgvector