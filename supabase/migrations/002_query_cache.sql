-- Critical Materials Knowledge Base — Query Response Cache
--
-- Caches fully-computed RAG responses keyed by a hash of the
-- normalized question + filters. The pipeline is the expensive
-- part (hybrid retrieval → rerank → generate → verify → follow-ups),
-- and demos repeat the same handful of questions. A 24h TTL keeps
-- the cache fresh enough that corpus updates are reflected the next
-- day without manual invalidation.

CREATE TABLE IF NOT EXISTS query_cache (
    cache_key TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    response JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- TTL sweeps and `WHERE created_at > now() - interval '24 hours'`
-- lookups both benefit from an index on created_at.
CREATE INDEX IF NOT EXISTS idx_query_cache_created_at
    ON query_cache(created_at);
