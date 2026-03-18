-- FAQs table with vector embeddings for semantic search
CREATE TABLE faqs (
  id BIGSERIAL PRIMARY KEY,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  category TEXT,
  embedding extensions.vector(384),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Similarity search RPC (called from Edge Function via supabase.rpc())
-- Uses inner product (<#>) since gte-small embeddings are normalized (equivalent to cosine similarity but faster)
CREATE OR REPLACE FUNCTION match_faqs(
  query_embedding extensions.vector(384),
  match_threshold FLOAT DEFAULT 0.8
)
RETURNS SETOF faqs
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT *
  FROM faqs
  WHERE faqs.embedding <#> query_embedding < -match_threshold
  ORDER BY faqs.embedding <#> query_embedding;
END;
$$;
