-- Source Enhancement Migration SQL
-- Add page_number, line_start, line_end columns to mevzuat_embeddings table
-- Run this on your Supabase database to enable enhanced source tracking

-- 1. Add new columns to embeddings table
ALTER TABLE public.mevzuat_embeddings 
ADD COLUMN IF NOT EXISTS page_number INTEGER,
ADD COLUMN IF NOT EXISTS line_start INTEGER,
ADD COLUMN IF NOT EXISTS line_end INTEGER;

-- 2. Update the search_embeddings function to return new fields
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

-- 3. Create index for better performance on page_number queries
CREATE INDEX IF NOT EXISTS idx_mevzuat_embeddings_page_number 
ON public.mevzuat_embeddings(page_number);

-- 4. Create composite index for page and line range queries
CREATE INDEX IF NOT EXISTS idx_mevzuat_embeddings_source_location 
ON public.mevzuat_embeddings(document_id, page_number, line_start);

-- 5. Add comment for documentation
COMMENT ON COLUMN public.mevzuat_embeddings.page_number IS 'PDF page number where this content chunk is located';
COMMENT ON COLUMN public.mevzuat_embeddings.line_start IS 'Starting line number within the page';
COMMENT ON COLUMN public.mevzuat_embeddings.line_end IS 'Ending line number within the page';

-- Migration completed successfully
-- New PDF documents will automatically include source information
-- Existing documents can be reprocessed to add source metadata