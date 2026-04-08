-- Critical Materials Knowledge Base — Initial Schema
-- Requires: pgvector extension enabled in Supabase dashboard

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- documents table
-- ============================================================
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    source_url TEXT,
    document_type TEXT NOT NULL CHECK (document_type IN (
        'usgs_mcs', 'gao_report', 'crs_report', 'dpa_announcement',
        'industry', 'regulatory', 'custom_analysis', 'news', 'doe_report'
    )),
    date_published DATE,
    materials TEXT[],
    file_path TEXT,
    file_hash TEXT,
    total_chunks INTEGER,
    ingested_at TIMESTAMPTZ DEFAULT now(),
    metadata JSONB
);

CREATE UNIQUE INDEX idx_documents_file_hash ON documents(file_hash);

-- ============================================================
-- chunks table (pgvector + full-text search)
-- ============================================================
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    section_title TEXT,
    page_numbers INTEGER[],
    materials TEXT[],
    embedding vector(1536),
    fts_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_chunks_fts ON chunks USING gin (fts_vector);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_materials ON chunks USING gin (materials);

-- ============================================================
-- extracted_entities table
-- ============================================================
CREATE TABLE extracted_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'Material', 'Company', 'Facility', 'WeaponSystem',
        'Regulation', 'Country', 'DPAAward', 'StockpileItem'
    )),
    properties JSONB,
    source_chunk_id UUID REFERENCES chunks(id),
    confidence FLOAT NOT NULL DEFAULT 0.5,
    verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_entities_name ON extracted_entities(name);
CREATE INDEX idx_entities_type ON extracted_entities(entity_type);
CREATE INDEX idx_entities_verified ON extracted_entities(verified);

-- ============================================================
-- extracted_relationships table
-- ============================================================
CREATE TABLE extracted_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID REFERENCES extracted_entities(id),
    target_entity_id UUID REFERENCES extracted_entities(id),
    relationship_type TEXT NOT NULL,
    properties JSONB,
    source_chunk_id UUID REFERENCES chunks(id),
    confidence FLOAT NOT NULL DEFAULT 0.5,
    verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_relationships_type ON extracted_relationships(relationship_type);

-- ============================================================
-- query_log table
-- ============================================================
CREATE TABLE query_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    answer TEXT,
    sources JSONB,
    query_type TEXT,
    retrieval_method TEXT,
    chunks_retrieved INTEGER,
    chunks_after_rerank INTEGER,
    verification_verdict TEXT,
    verification_issues JSONB,
    latency_ms INTEGER,
    user_feedback TEXT CHECK (user_feedback IN ('thumbs_up', 'thumbs_down')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- RPC functions for vector and full-text search
-- ============================================================

-- Vector similarity search
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(1536),
    match_count INT DEFAULT 20,
    filter_materials TEXT[] DEFAULT NULL,
    filter_doc_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    chunk_index INT,
    text TEXT,
    section_title TEXT,
    page_numbers INT[],
    materials TEXT[],
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        c.chunk_index,
        c.text,
        c.section_title,
        c.page_numbers,
        c.materials,
        c.metadata,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunks c
    WHERE
        (filter_materials IS NULL OR c.materials && filter_materials)
        AND (filter_doc_type IS NULL OR c.metadata->>'document_type' = filter_doc_type)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Full-text search
CREATE OR REPLACE FUNCTION fts_search_chunks(
    search_query TEXT,
    match_count INT DEFAULT 20,
    filter_materials TEXT[] DEFAULT NULL,
    filter_doc_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    chunk_index INT,
    text TEXT,
    section_title TEXT,
    page_numbers INT[],
    materials TEXT[],
    metadata JSONB,
    rank REAL
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        c.chunk_index,
        c.text,
        c.section_title,
        c.page_numbers,
        c.materials,
        c.metadata,
        ts_rank(c.fts_vector, plainto_tsquery('english', search_query)) AS rank
    FROM chunks c
    WHERE
        c.fts_vector @@ plainto_tsquery('english', search_query)
        AND (filter_materials IS NULL OR c.materials && filter_materials)
        AND (filter_doc_type IS NULL OR c.metadata->>'document_type' = filter_doc_type)
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$;
