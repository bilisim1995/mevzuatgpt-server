-- ================================================
-- SUPABASE SOURCE ENHANCEMENT MIGRATION - FIXED
-- MevzuatGPT - PDF Source Tracking System
-- ================================================

-- 1. Add new columns to embeddings table for PDF source tracking
ALTER TABLE public.mevzuat_embeddings 
ADD COLUMN IF NOT EXISTS page_number INTEGER,
ADD COLUMN IF NOT EXISTS line_start INTEGER,
ADD COLUMN IF NOT EXISTS line_end INTEGER;

-- 2. Create or replace the search_embeddings function with source fields
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
    document_filename text,
    chunk_index integer,
    metadata jsonb
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
        d.filename AS document_filename,
        e.chunk_index,
        e.metadata
    FROM mevzuat_embeddings e
    JOIN mevzuat_documents d ON e.document_id = d.id
    WHERE 
        d.status = 'completed'
        AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- 3. Create performance indexes for source tracking
CREATE INDEX IF NOT EXISTS idx_mevzuat_embeddings_page_number 
ON public.mevzuat_embeddings(page_number);

CREATE INDEX IF NOT EXISTS idx_mevzuat_embeddings_source_location 
ON public.mevzuat_embeddings(document_id, page_number, line_start);

CREATE INDEX IF NOT EXISTS idx_mevzuat_embeddings_line_range 
ON public.mevzuat_embeddings(line_start, line_end);

-- 4. Add comments for documentation
COMMENT ON COLUMN public.mevzuat_embeddings.page_number IS 'PDF page number where this content chunk is located';
COMMENT ON COLUMN public.mevzuat_embeddings.line_start IS 'Starting line number within the page';
COMMENT ON COLUMN public.mevzuat_embeddings.line_end IS 'Ending line number within the page';

-- 5. Admin user creation (FIXED - no ON CONFLICT)
DO $$
DECLARE
    user_id uuid;
    profile_exists boolean := false;
BEGIN
    -- Check if user already exists
    SELECT id INTO user_id FROM auth.users WHERE email = 'admin@mevzuatgpt.com';
    
    IF user_id IS NULL THEN
        -- Create new admin user
        user_id := gen_random_uuid();
        
        INSERT INTO auth.users (
            id,
            instance_id,
            email,
            encrypted_password,
            email_confirmed_at,
            created_at,
            updated_at,
            raw_app_meta_data,
            raw_user_meta_data,
            is_super_admin,
            role,
            aud,
            confirmation_token,
            email_confirmed_at
        ) VALUES (
            user_id,
            '00000000-0000-0000-0000-000000000000',
            'admin@mevzuatgpt.com',
            crypt('AdminMevzuat2025!', gen_salt('bf')),
            NOW(),
            NOW(),
            NOW(),
            '{"provider": "email", "providers": ["email"]}',
            '{"role": "admin", "full_name": "Admin User"}',
            false,
            'authenticated',
            'authenticated',
            '',
            NOW()
        );
        
        RAISE NOTICE 'Created new admin user with ID: %', user_id;
    ELSE
        RAISE NOTICE 'Admin user already exists with ID: %', user_id;
    END IF;
    
    -- Check if profile exists
    SELECT EXISTS(SELECT 1 FROM public.user_profiles WHERE id = user_id) INTO profile_exists;
    
    IF NOT profile_exists THEN
        -- Create user profile
        INSERT INTO public.user_profiles (
            id,
            full_name,
            role,
            created_at,
            updated_at
        ) VALUES (
            user_id,
            'Admin User',
            'admin',
            NOW(),
            NOW()
        );
        RAISE NOTICE 'Created admin user profile';
    ELSE
        -- Update existing profile
        UPDATE public.user_profiles 
        SET role = 'admin', 
            full_name = 'Admin User',
            updated_at = NOW()
        WHERE id = user_id;
        RAISE NOTICE 'Updated existing admin user profile';
    END IF;
    
END $$;

-- 6. Update RLS policies to ensure admin access
DROP POLICY IF EXISTS "Admins can manage all data" ON public.mevzuat_documents;
CREATE POLICY "Admins can manage all data" ON public.mevzuat_documents
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

DROP POLICY IF EXISTS "Admins can manage all embeddings" ON public.mevzuat_embeddings;
CREATE POLICY "Admins can manage all embeddings" ON public.mevzuat_embeddings
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- 7. Verify migration success
DO $$
DECLARE
    col_count INTEGER;
    admin_count INTEGER;
BEGIN
    -- Check if new columns were added
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns 
    WHERE table_name = 'mevzuat_embeddings' 
    AND column_name IN ('page_number', 'line_start', 'line_end');
    
    -- Check if admin user was created
    SELECT COUNT(*) INTO admin_count
    FROM auth.users u
    WHERE u.email = 'admin@mevzuatgpt.com';
    
    RAISE NOTICE '================================================';
    RAISE NOTICE 'MIGRATION RESULTS:';
    RAISE NOTICE '- Source tracking columns added: % of 3', col_count;
    RAISE NOTICE '- Admin user exists: %', (admin_count > 0);
    RAISE NOTICE '- Search function updated: YES';
    RAISE NOTICE '- Performance indexes created: YES';
    RAISE NOTICE '================================================';
    
    IF col_count = 3 AND admin_count > 0 THEN
        RAISE NOTICE 'SUCCESS: Migration completed successfully!';
        RAISE NOTICE 'Next: Update document processor to use create_embedding_with_sources()';
    ELSE
        RAISE NOTICE 'WARNING: Migration may be incomplete. Please check manually.';
    END IF;
END $$;

-- Migration completed!
-- 
-- NEXT STEPS:
-- 1. Update tasks/document_processor.py line 175:
--    FROM: create_embedding()
--    TO:   create_embedding_with_sources() 
--
-- 2. Test new PDF upload to verify source tracking
-- 3. Test ask endpoint for enhanced source information