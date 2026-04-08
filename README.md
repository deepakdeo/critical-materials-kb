# Critical Materials Knowledge Base

A hybrid RAG and GraphRAG-powered knowledge base for querying U.S. critical materials supply chain data. Built for the Center for Materials Criticality (CMC) to enable rapid, sourced answers to supply chain questions using government reports, industry data, and open-source intelligence.

## Architecture

The system combines three retrieval strategies for maximum accuracy:

1. **Hybrid Retrieval** — parallel vector search (pgvector) and BM25 full-text search (Supabase tsvector), merged via Reciprocal Rank Fusion (RRF)
2. **Cross-Encoder Reranking** — a local cross-encoder model (ms-marco-MiniLM-L-6-v2) reranks the top 30 candidates down to the best 5-8
3. **Self-Corrective Verification (CRAG)** — a second LLM pass verifies that every citation is real and every claim is grounded in the retrieved context

For relational queries ("Who supplies tungsten to General Dynamics?"), a curated Neo4j knowledge graph provides supply chain traversals alongside text retrieval.

Every answer includes source citations in `[Source Name, Page/Section]` format.

## Setup

### Prerequisites

- Python 3.11+
- A [Supabase](https://supabase.com/) project with pgvector enabled
- OpenAI API key (for embeddings)
- Anthropic API key (for generation)
- (Optional) Neo4j AuraDB instance for knowledge graph features

### Installation

```bash
git clone https://github.com/deepakdeo/critical-materials-kb.git
cd critical-materials-kb
pip install -e ".[dev]"
```

### Environment Variables

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

Required variables: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`.

### Database Setup

Run the SQL migration in your Supabase SQL editor:

```
supabase/migrations/001_initial_schema.sql
```

This creates all tables (documents, chunks with pgvector + FTS, extracted_entities, extracted_relationships, query_log) and RPC functions for search.

### Ingest Documents

```bash
python scripts/ingest_documents.py --source data/raw/usgs/ --doc-type usgs_mcs
python scripts/ingest_documents.py --source data/raw/gao/ --doc-type gao_report --materials tungsten,nickel
```

### Run the API

```bash
uvicorn src.api.main:app --reload
```

### Run the Frontend

```bash
streamlit run frontend/app.py
```

### Run Tests

```bash
pytest
ruff check src/ tests/
```

## Project Structure

```
critical-materials-kb/
├── src/
│   ├── config.py                 # Environment config and constants
│   ├── ingest/                   # Document loading, chunking, embedding
│   ├── store/                    # Supabase vector, FTS, and metadata operations
│   ├── graph/                    # Neo4j knowledge graph schema and operations
│   ├── retrieval/                # Vector, BM25, graph, hybrid retrieval + reranker
│   ├── generation/               # LLM generation, prompts, CRAG verifier
│   └── api/                      # FastAPI endpoints
├── frontend/                     # Streamlit chatbot UI
├── scripts/                      # CLI tools for ingestion and testing
├── tests/                        # pytest test suite
├── supabase/migrations/          # SQL schema migrations
├── data/                         # Raw documents and processed data
└── docs/                         # Architecture and data source documentation
```

## Related Repositories

- [materials-priority-tool](https://github.com/deepakdeo/materials-priority-tool) — Scoring dashboard for ranking critical materials by supply risk, strategic alignment, and production feasibility
