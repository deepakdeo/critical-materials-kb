# Critical Materials Knowledge Base (critical-materials-kb)

## Project Overview
A hybrid RAG and GraphRAG-powered knowledge base and chatbot for querying U.S. critical materials supply chain data. Built for the Center for Materials Criticality (CMC) to enable rapid, sourced answers to supply chain questions using government reports, industry data, and open-source intelligence.

## Core Purpose
Allow users to ask natural language questions like:
- "Which U.S. companies can produce tungsten powder from non-Chinese feedstock?"
- "What is the current U.S. import reliance for nickel?"
- "If China cuts tungsten exports, which DoD programs are affected?"
- "What DPA Title III awards have been made for critical materials in 2025?"

And receive accurate, cited, verifiable answers drawn from a curated document corpus.

## Design Philosophy
**Factual accuracy and verifiability above all else.** This tool is used by defense analysts and policy researchers who need to trust every number. The architecture prioritizes:
1. Hybrid retrieval (vector + BM25) to catch both semantic and exact-match results
2. Cross-encoder reranking to filter noise before the LLM sees it
3. Self-corrective generation that verifies answers are grounded in retrieved context
4. Curated knowledge graph for relational queries (not fully automated GraphRAG)
5. Every answer must cite its source document, page, and section

## Tech Stack
- **Language:** Python 3.11+
- **Framework:** FastAPI (backend API) + Streamlit (initial frontend, React later)
- **Database:** Supabase (PostgreSQL + pgvector for vector storage + full-text search for BM25 + metadata)
- **Knowledge Graph:** Neo4j AuraDB (free tier) with neo4j Python driver
- **Embeddings:** OpenAI text-embedding-3-small (primary), with fallback to local sentence-transformers
- **Reranker:** cross-encoder/ms-marco-MiniLM-L-6-v2 (local, free) or Cohere Rerank API
- **LLM:** Claude API via anthropic Python SDK (primary), with fallback config for OpenAI
- **Document Processing:** pdfplumber (PDFs), BeautifulSoup (HTML), unstructured (general)
- **Orchestration:** LangChain for RAG pipeline
- **Testing:** pytest
- **Linting:** ruff
- **Deployment:** Vercel (frontend) + Railway or Render (backend API) + Supabase (database)

## Project Structure
```
critical-materials-kb/
├── CLAUDE.md                          # This file
├── PROJECT.md                         # Full technical specification
├── README.md                          # Public-facing documentation
├── pyproject.toml                     # Python project config (dependencies, ruff, pytest)
├── .env.example                       # Template for environment variables
├── .gitignore
├── data/
│   ├── raw/                           # Original source documents (PDFs, HTML)
│   │   ├── usgs/                      # USGS MCS reports
│   │   ├── gao/                       # GAO reports
│   │   ├── crs/                       # Congressional Research Service
│   │   ├── dpa/                       # DPA Title III announcements
│   │   ├── industry/                  # Company filings, press releases
│   │   └── regulatory/               # DFARS, NDAA text
│   ├── processed/                     # Chunked text with metadata (JSON)
│   └── graph/                         # Entity/relationship extractions (JSON)
│       └── seed_data.json             # Manually curated supply chain graph data
├── src/
│   ├── __init__.py
│   ├── config.py                      # Environment config, constants
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── loader.py                  # Document loading (PDF, HTML, text)
│   │   ├── chunker.py                 # Section-aware chunking with metadata
│   │   ├── embedder.py                # Embedding generation (OpenAI + local fallback)
│   │   ├── entity_extractor.py        # LLM-based entity/relationship extraction
│   │   └── pipeline.py                # End-to-end ingestion orchestration
│   ├── store/
│   │   ├── __init__.py
│   │   ├── vector_store.py            # Supabase pgvector operations
│   │   ├── fulltext_store.py          # Supabase full-text search (BM25) operations
│   │   └── metadata_store.py          # Document metadata CRUD
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── schema.py                  # Node/edge type definitions (Pydantic models)
│   │   ├── builder.py                 # Graph construction from extracted entities
│   │   ├── neo4j_store.py             # Neo4j read/write operations
│   │   └── queries.py                 # Pre-built Cypher query templates
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── vector_retriever.py        # Semantic similarity search (pgvector)
│   │   ├── bm25_retriever.py          # Keyword/exact-match search (Supabase FTS)
│   │   ├── graph_retriever.py         # Graph-based retrieval (Cypher from NL)
│   │   ├── hybrid_retriever.py        # Vector + BM25 fusion via Reciprocal Rank Fusion
│   │   ├── reranker.py                # Cross-encoder reranking of retrieved chunks
│   │   └── query_classifier.py        # Classify query type (factual/relational/analytical)
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── prompts.py                 # System and user prompt templates
│   │   ├── generator.py               # LLM answer generation with citations
│   │   ├── verifier.py                # Self-corrective check: is answer grounded in context?
│   │   └── chains.py                  # End-to-end retrieval → generation → verification chain
│   └── api/
│       ├── __init__.py
│       ├── main.py                    # FastAPI app entry point
│       ├── routes/
│       │   ├── query.py               # /query endpoint
│       │   ├── ingest.py              # /ingest endpoint (admin)
│       │   ├── graph.py               # /graph endpoints
│       │   └── health.py              # /health endpoint
│       └── models.py                  # Pydantic request/response models
├── frontend/
│   └── app.py                         # Streamlit chatbot UI
├── scripts/
│   ├── ingest_documents.py            # CLI: ingest a folder of documents
│   ├── build_graph.py                 # CLI: build/update knowledge graph from extracted entities
│   ├── seed_graph.py                  # CLI: seed graph with manually curated supply chain data
│   └── test_query.py                  # CLI: quick query test
├── tests/
│   ├── __init__.py
│   ├── test_loader.py
│   ├── test_chunker.py
│   ├── test_embedder.py
│   ├── test_bm25_retriever.py
│   ├── test_hybrid_retriever.py
│   ├── test_reranker.py
│   ├── test_verifier.py
│   ├── test_generator.py
│   └── test_api.py
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql     # Documents, chunks (pgvector + FTS), query_log tables
└── docs/
    ├── architecture.md                # System architecture diagram and explanation
    ├── data_sources.md                # Catalog of all source documents
    └── graph_schema.md                # Knowledge graph entity/relationship definitions
```

## Coding Conventions
- Use type hints on all function signatures
- Docstrings on all public functions (Google style)
- Keep functions short and single-purpose
- Use Pydantic models for all data structures passed between modules
- Environment variables for all secrets and configuration (never hardcode API keys)
- All database queries go through dedicated store modules, never raw SQL in business logic
- Logging via Python's logging module, not print statements
- Error handling: catch specific exceptions, provide useful error messages
- All retrieval modules must return a standardized RetrievalResult Pydantic model

## Key Design Decisions

### 1. Hybrid Retrieval (Vector + BM25)
Vector search alone misses exact terms (document IDs like "GAO-24-107176", regulatory references like "DFARS 225.7018", specific company names). BM25 alone misses semantic connections. Running both in parallel and merging via Reciprocal Rank Fusion (RRF) consistently outperforms either alone in benchmarks. Supabase supports both pgvector and full-text search (tsvector) natively, so this adds no infrastructure cost.

### 2. Cross-Encoder Reranking
Initial retrieval (hybrid) casts a wide net: retrieve top 20-30 candidates. Then a cross-encoder (ms-marco-MiniLM-L-6-v2, runs locally, free) scores each candidate against the original query with full attention. Keep top 5-8 for the LLM. This dramatically improves context quality and reduces hallucination.

### 3. Self-Corrective Generation (CRAG pattern)
After the LLM generates an answer, a verification step checks:
- Does every cited source actually appear in the retrieved context?
- Does every factual claim trace to a specific chunk?
- Are there claims that aren't supported by any retrieved chunk?
If verification fails, the system either re-retrieves with a reformulated query or returns "insufficient data to answer this question" rather than hallucinating. This costs one additional LLM call but is non-negotiable for a defense/policy use case.

### 4. Chunking Strategy
Chunk by document section/heading, not by fixed token count. Preserve section titles and document metadata in each chunk. Target 500-1000 tokens per chunk with 100-token overlap. Each chunk carries full provenance metadata (source, date, page, section, materials mentioned).

### 5. Curated Knowledge Graph
The knowledge graph is seeded with manually verified supply chain data from our existing analysis (companies, facilities, materials, weapon systems, regulations, DPA awards). New entities are extracted from documents via LLM but flagged as "auto-extracted" with a confidence score. Only manually verified or high-confidence entities are used for graph-based retrieval. This prevents graph pollution from bad extractions.

### 6. Citation Format
Every generated answer must include source citations in the format [Source Name, Page/Section]. The generation prompt enforces this. The verifier checks that citations are real.

### 7. Query Classification
Before retrieval, classify the query to route it optimally:
- FACTUAL → hybrid retrieval (vector + BM25)
- RELATIONAL → graph traversal + supporting vector context
- ANALYTICAL → graph traversal + hybrid retrieval + multi-step reasoning
- REGULATORY → hybrid retrieval filtered to regulatory documents
- COMPARATIVE → multiple targeted retrievals + synthesis

Classification uses rule-based heuristics first (pattern matching on query structure), with LLM fallback for ambiguous queries.

## Environment Variables Required
```
# LLM and Embeddings
ANTHROPIC_API_KEY=           # Claude API for generation and verification
OPENAI_API_KEY=              # OpenAI embeddings (text-embedding-3-small)

# Database
SUPABASE_URL=                # Supabase project URL
SUPABASE_KEY=                # Supabase anon key
SUPABASE_SERVICE_KEY=        # Supabase service role key (for admin operations)

# Knowledge Graph
NEO4J_URI=                   # Neo4j AuraDB connection URI
NEO4J_USER=                  # Neo4j username
NEO4J_PASSWORD=              # Neo4j password

# Optional
COHERE_API_KEY=              # Cohere Rerank API (if not using local cross-encoder)
EMBEDDING_MODEL=text-embedding-3-small  # Override embedding model
LLM_MODEL=claude-sonnet-4-20250514       # Override LLM model
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2  # Override reranker
```

## Commands
```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/

# Ingest documents
python scripts/ingest_documents.py --source data/raw/usgs/ --doc-type usgs_mcs

# Build knowledge graph from extracted entities
python scripts/build_graph.py

# Seed graph with curated supply chain data
python scripts/seed_graph.py

# Run API server
uvicorn src.api.main:app --reload

# Run Streamlit frontend
streamlit run frontend/app.py

# Quick query test
python scripts/test_query.py "What is U.S. import reliance for tungsten?"
```

## Related Repositories
- [materials-priority-tool](https://github.com/deepakdeo/materials-priority-tool) — Scoring dashboard for ranking critical materials by supply risk, strategic alignment, and production feasibility
