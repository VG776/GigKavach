"""
Database migration: Create share_tokens table for WhatsApp integration
This table stores shareable tokens generated for workers to access their profiles via WhatsApp links.
"""

# Migration name: 20240413_create_share_tokens_table

sql_migration = """
-- Create share_tokens table for worker PWA shareable links
CREATE TABLE IF NOT EXISTS public.share_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Foreign key to workers
  worker_id UUID NOT NULL REFERENCES public.workers(id) ON DELETE CASCADE,
  
  -- Token value (unique, indexed for fast lookups)  
  token TEXT NOT NULL UNIQUE,
  
  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  
  -- Usage tracking
  is_used BOOLEAN DEFAULT FALSE,
  use_count INTEGER DEFAULT 0,
  max_uses INTEGER DEFAULT NULL, -- NULL = unlimited uses
  
  -- Metadata
  created_by TEXT DEFAULT 'manual', -- 'whatsapp', 'email', 'manual'
  notes TEXT,
  
  -- Indexing for performance
  CONSTRAINT share_tokens_valid_expiry CHECK (expires_at > created_at),
  CONSTRAINT share_tokens_nonnegative_uses CHECK (use_count >= 0)
);

-- Create indexes for common queries
CREATE INDEX idx_share_tokens_token ON public.share_tokens(token);
CREATE INDEX idx_share_tokens_worker_id ON public.share_tokens(worker_id);
CREATE INDEX idx_share_tokens_expires_at ON public.share_tokens(expires_at);
CREATE INDEX idx_share_tokens_created_by ON public.share_tokens(created_by);

-- Enable RLS (Row Level Security)
ALTER TABLE public.share_tokens ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- 1. Allow service role (backend) to read share_tokens
CREATE POLICY "Service role can read share tokens"
  ON public.share_tokens
  FOR SELECT
  TO service_role
  USING (TRUE);

-- 2. Allow service role to insert share_tokens
CREATE POLICY "Service role can create share tokens"
  ON public.share_tokens
  FOR INSERT
  TO service_role
  WITH CHECK (TRUE);

-- 3. Allow service role to update share_tokens (for tracking uses)
CREATE POLICY "Service role can update share tokens"
  ON public.share_tokens
  FOR UPDATE
  TO service_role
  USING (TRUE)
  WITH CHECK (TRUE);

-- 4. Allow service role to delete share_tokens (for revocation)
CREATE POLICY "Service role can delete share tokens"
  ON public.share_tokens
  FOR DELETE
  TO service_role
  USING (TRUE);

-- 5. Allow workers to read their own share tokens
CREATE POLICY "Workers can read their own share tokens"
  ON public.share_tokens
  FOR SELECT
  USING (worker_id = auth.uid());

-- 6. Disallow workers from directly modifying share_tokens
CREATE POLICY "Workers cannot modify share tokens directly"
  ON public.share_tokens
  FOR UPDATE
  USING (FALSE);

-- Add comments for documentation
COMMENT ON TABLE public.share_tokens IS 
  'Shareable tokens for worker PWA links via WhatsApp bot. Short-lived tokens allow workers to access their profile/status/history via public links.';

COMMENT ON COLUMN public.share_tokens.token IS 
  'URL-safe random token used in shareable links';

COMMENT ON COLUMN public.share_tokens.max_uses IS 
  'Maximum number of times this token can be used. NULL = unlimited.';

COMMENT ON COLUMN public.share_tokens.created_by IS 
  'Source of token generation: whatsapp bot, email, or manual creation';
"""

# Rollback migration (if needed)
rollback_sql = """
-- Drop share_tokens table
DROP TABLE IF EXISTS public.share_tokens CASCADE;
"""

def execute_migration(supabase_client):
    """Execute the migration using Supabase client"""
    try:
        print("Creating share_tokens table...")
        # Supabase admin API would execute the SQL
        # This is a template - actual execution would go through SQL editor or migrations tool
        print("Migration would execute:")
        print(sql_migration)
        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("SQL Migration for share_tokens table:")
    print(sql_migration)
