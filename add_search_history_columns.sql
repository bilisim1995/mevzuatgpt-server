-- Add enhanced search history columns to search_logs table
ALTER TABLE search_logs 
ADD COLUMN IF NOT EXISTS response TEXT,
ADD COLUMN IF NOT EXISTS sources JSONB,
ADD COLUMN IF NOT EXISTS reliability_score FLOAT,
ADD COLUMN IF NOT EXISTS credits_used INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS institution_filter VARCHAR(100);

-- Create index for faster filtering
CREATE INDEX IF NOT EXISTS idx_search_logs_institution ON search_logs (institution_filter);
CREATE INDEX IF NOT EXISTS idx_search_logs_reliability ON search_logs (reliability_score);
CREATE INDEX IF NOT EXISTS idx_search_logs_credits ON search_logs (credits_used);