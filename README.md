# Critical Materials Knowledge Base

A hybrid RAG and GraphRAG-powered knowledge base for querying U.S. critical materials supply chain data. Enables rapid, sourced answers to supply chain questions using government reports, industry data, and open-source intelligence.

Designed for defense analysts, policy researchers, and supply chain professionals working with critical materials.

## Features

- **Natural language Q&A** — ask questions like "If China cuts tungsten exports, which DoD programs are affected?" and get cited, verified answers
- **Hybrid retrieval** — parallel vector search (pgvector) + BM25 full-text search, merged via Reciprocal Rank Fusion
- **Knowledge graph** — Neo4j graph of supply chain relationships (companies, materials, countries, weapon systems, regulations, DPA awards) for relational queries
- **Self-corrective verification (CRAG)** — every answer is fact-checked against retrieved context; ungrounded claims are flagged or rejected
- **Interactive graph visualization** — D3-force physics simulation with drag, zoom, hover highlighting, and click-to-explore
- **Source citations** — every claim links to its source document, page, and section with expandable text previews
- **Follow-up suggestions** — AI-generated follow-up questions based on the conversation
- **Confidence scoring** — visual confidence indicator based on verification, evidence quality, and retrieval method
- **Multi-turn context** — conversations carry context for follow-up questions
- **Source document library** — browse all 20 indexed documents with links to original public sources
- **Export** — copy any answer as formatted Markdown with sources and metadata
- **Dark mode** — full dark/light theme support

## Architecture

```
User Query → Query Classifier → Hybrid Retriever (Vector + BM25 + RRF)
                               → Graph Retriever (Neo4j Cypher)
                               → Cross-Encoder Reranker
                               → LLM Generator (Claude) + Follow-up Generation
                               → CRAG Verifier → Confidence Scoring
                               → Cited Answer + Sources + Graph Data
```

**Retrieval strategies by query type:**
| Query Type | Retrieval Method |
|-----------|-----------------|
| FACTUAL | Hybrid (vector + BM25) |
| RELATIONAL | Graph traversal + hybrid |
| ANALYTICAL | Graph + hybrid + multi-step |
| REGULATORY | Graph + hybrid (regulatory focus) |
| COMPARATIVE | Multiple targeted retrievals |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite + Tailwind CSS v4 |
| Graph Viz | D3-force + d3-drag + d3-zoom |
| Backend | FastAPI (Python) |
| Database | Supabase (PostgreSQL + pgvector + FTS) |
| Knowledge Graph | Neo4j AuraDB |
| Embeddings | OpenAI text-embedding-3-small |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 (local) |
| LLM | Claude (Anthropic API) |

## Document Corpus

20 curated documents across 7 categories:

- **USGS** — Mineral Commodity Summaries 2025, 2026
- **DOE** — Critical Materials Assessment 2023, CMM Program Overview 2025
- **GAO** — Critical materials procurement and stockpile reports
- **CRS** — Congressional Research Service reports on NDS, specialty metals, critical minerals policy
- **DPA** — Defense Production Act Title III award announcements
- **DFARS** — Federal Register final rule on tungsten sourcing restrictions
- **Industry** — Company pages (Kennametal, GTP, Elmet, 6K Additive, RTX)

## Knowledge Graph

67 curated nodes and 86 relationships covering:
- 18 materials, 18 companies, 13 countries, 3 facilities
- 7 weapon systems (F-35, M1 Abrams, Patriot, Javelin, etc.)
- 4 regulations (DFARS 225.7018, 10 USC 4872, etc.)
- 4 DPA Title III awards

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for React frontend)
- [Supabase](https://supabase.com/) project with pgvector enabled
- OpenAI API key (embeddings)
- Anthropic API key (generation)
- Neo4j AuraDB instance (knowledge graph)

### Installation

```bash
git clone https://github.com/deepakdeo/critical-materials-kb.git
cd critical-materials-kb

# Backend
pip install -e ".[dev]"
cp .env.example .env  # Fill in your API keys

# Frontend
cd frontend-react
npm install
```

### Database Setup

Run the SQL migration in your Supabase SQL editor:

```
supabase/migrations/001_initial_schema.sql
```

### Ingest Documents

```bash
python scripts/ingest_documents.py --source data/raw/usgs/ --doc-type usgs_mcs
python scripts/ingest_documents.py --source data/raw/gao/ --doc-type gao_report --materials tungsten,nickel
# ... repeat for each document category
```

### Seed Knowledge Graph

```bash
python scripts/seed_graph.py --clear --stats
```

### Run

```bash
# Backend API
uvicorn src.api.main:app --reload

# React frontend (in a separate terminal)
cd frontend-react
npm run dev
```

The frontend runs at http://localhost:5173 and proxies API requests to the backend at http://localhost:8000.

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
│   ├── graph/                    # Neo4j knowledge graph (schema, queries, builder)
│   ├── retrieval/                # Vector, BM25, graph, hybrid retrieval + reranker
│   ├── generation/               # LLM generation, prompts, CRAG verifier, chains
│   └── api/                      # FastAPI endpoints and source URL mapping
├── frontend-react/               # React 19 + Vite + Tailwind v4
│   └── src/
│       ├── components/           # MessageBubble, GraphVisualization, Sidebar, etc.
│       └── hooks/                # useQuery, useTheme
├── frontend/                     # Streamlit chatbot UI (legacy)
├── scripts/                      # CLI tools (ingest, seed graph, test query)
├── tests/                        # pytest test suite
├── supabase/migrations/          # SQL schema migrations
├── data/
│   ├── raw/                      # Source documents (PDF, HTML)
│   └── graph/seed_data.json      # Curated supply chain graph data
└── docs/                         # Architecture and data source documentation
```

## Related Repositories

- [materials-priority-tool](https://github.com/deepakdeo/materials-priority-tool) — Scoring dashboard for ranking critical materials by supply risk, strategic alignment, and production feasibility
