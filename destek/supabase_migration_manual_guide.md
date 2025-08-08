# Supabase Manual Migration Guide - Source Enhancement

## Problem
Yeni PDF kaynak takip sistemi için `mevzuat_embeddings` tablosuna yeni kolonlar eklememiz gerekiyor:
- `page_number` INTEGER
- `line_start` INTEGER  
- `line_end` INTEGER

## Manual Migration Steps

### 1. Supabase Dashboard'a Git
1. https://supabase.com/dashboard'a git
2. Projenizi seçin
3. Sol menüden **SQL Editor**'ı seçin

### 2. Migration SQL'i Çalıştır
Aşağıdaki SQL kodunu SQL Editor'a yapıştırın ve çalıştırın:

```sql
-- Source Enhancement Migration
-- Add new columns for PDF source tracking

-- 1. Add columns to embeddings table
ALTER TABLE public.mevzuat_embeddings 
ADD COLUMN IF NOT EXISTS page_number INTEGER,
ADD COLUMN IF NOT EXISTS line_start INTEGER,
ADD COLUMN IF NOT EXISTS line_end INTEGER;

-- 2. Update search function to return new fields
CREATE OR REPLACE FUNCTION search_embeddings(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    content text,
    page_number integer,
    line_start integer,
    line_end integer,
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
        e.page_number,
        e.line_start,
        e.line_end,
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

-- 3. Create performance indexes
CREATE INDEX IF NOT EXISTS idx_mevzuat_embeddings_page_number 
ON public.mevzuat_embeddings(page_number);

CREATE INDEX IF NOT EXISTS idx_mevzuat_embeddings_source_location 
ON public.mevzuat_embeddings(document_id, page_number, line_start);

-- 4. Add documentation
COMMENT ON COLUMN public.mevzuat_embeddings.page_number IS 'PDF page number where content is located';
COMMENT ON COLUMN public.mevzuat_embeddings.line_start IS 'Starting line number within the page';  
COMMENT ON COLUMN public.mevzuat_embeddings.line_end IS 'Ending line number within the page';
```

### 3. Migration Doğrulaması
Migration başarılı ise aşağıdaki SQL ile test edin:

```sql
-- Test the new columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'mevzuat_embeddings' 
AND column_name IN ('page_number', 'line_start', 'line_end');
```

### 4. Code Update
Migration tamamlandıktan sonra `tasks/document_processor.py` dosyasında:
- `create_embedding` metodunu `create_embedding_with_sources` ile değiştir
- Source enhancement sisteminin tam potansiyelini kullan

## Current Status
Şu anda sistem backward compatible modda çalışıyor:
- Source bilgileri metadata'da saklanıyor  
- Yeni PDF'ler parse ediliyor ve chunking yapılıyor
- Manual migration sonrası tam source enhancement aktif olacak

## Migration Sonrası Faydalar
✅ PDF'lerin sayfa numaraları     
✅ Satır aralığı bilgileri        
✅ Doğrudan PDF linkler          
✅ Akademik referans formatı      
✅ Gelişmiş arama deneyimi