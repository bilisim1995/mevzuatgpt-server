-- Bakım modu tablosu ve politikaları oluşturma SQL
-- Bu dosya Supabase SQL Editor'da çalıştırılacak

-- 1. Bakım modu tablosu oluştur
CREATE TABLE IF NOT EXISTS maintenance_mode (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    is_enabled BOOLEAN NOT NULL DEFAULT false,
    title VARCHAR(200) DEFAULT 'Sistem Bakımda',
    message TEXT DEFAULT 'Sistem geçici olarak bakım modunda. Lütfen daha sonra tekrar deneyin.',
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    updated_by UUID,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Unique constraint - sadece bir kayıt olsun
CREATE UNIQUE INDEX IF NOT EXISTS maintenance_mode_single_row ON maintenance_mode ((true));

-- 3. RLS etkinleştir
ALTER TABLE maintenance_mode ENABLE ROW LEVEL SECURITY;

-- 4. Eski politikaları temizle
DROP POLICY IF EXISTS "maintenance_mode_read_all" ON maintenance_mode;
DROP POLICY IF EXISTS "maintenance_mode_admin_update" ON maintenance_mode;

-- 5. Yeni politikalar oluştur
-- Herkes okuyabilir (maintenance durumu public)
CREATE POLICY "maintenance_mode_read_all" ON maintenance_mode FOR SELECT USING (true);

-- Sadece admin güncelleyebilir
CREATE POLICY "maintenance_mode_admin_update" ON maintenance_mode FOR ALL 
USING (
  EXISTS (
    SELECT 1 FROM user_profiles 
    WHERE id = auth.uid() AND role = 'admin'
  )
);

-- 6. İlk bakım modu kaydı ekle (sadece yoksa)
INSERT INTO maintenance_mode (is_enabled, title, message) 
VALUES (false, 'Sistem Bakımda', 'Sistem geçici olarak bakım modunda. Lütfen daha sonra tekrar deneyin.')
ON CONFLICT DO NOTHING;

-- 7. Test sorgusu
SELECT 'Bakım modu tablosu başarıyla oluşturuldu!' as status, 
       count(*) as kayit_sayisi 
FROM maintenance_mode;