# PROJECT.md — Critical Materials Knowledge Base

## 1. Problem Statement

The U.S. defense industrial base depends on critical materials (tungsten, nickel, rare earths, titanium, cobalt, etc.) sourced through complex global supply chains. Information about these supply chains is scattered across dozens of government reports (USGS, GAO, CRS, DOE), regulatory documents (DFARS, NDAA), industry filings, and news sources. Analysts at the Center for Materials Criticality (CMC) currently spend hours manually cross-referencing these sources to answer basic supply chain questions.

This project builds a searchable knowledge base with a natural language chatbot interface that can answer supply chain questions instantly, with full source citations and verified accuracy.

## 2. Target Users

- CMC analysts and researchers
- DoD program managers evaluating supply chain risks
- Policy analysts tracking critical materials legislation
- Defense industry supply chain professionals

## 3. Document Corpus (Initial)

### Government Reports
| Document | Source | Type | Content |
|---|---|---|---|
| Mineral Commodity Summaries 2026 | USGS | PDF, ~200 pages | Production, imports, consumption, prices for ~90 commodities |
| Mineral Commodity Summaries 2025 | USGS | PDF | Prior year for trend comparison |
| GAO-24-107176 | GAO | PDF | Critical materials procurement requirements, DFARS timelines |
| GAO-24-106959 | GAO | PDF | National Defense Stockpile shortfalls |
| CRS R47833 | CRS | PDF | NDS emergency access policy |
| CRS IF11226 | CRS | PDF | Specialty metals and sensitive materials primer |
| CRS R47982 | CRS | PDF | Critical minerals list and national policy |
| DARPA OPEN solicitation | DARPA | PDF/HTML | Materials price/supply/demand forecasting |
| DOE Critical Materials Assessment 2023 | DOE | PDF | Criticality categories for energy materials |

### Regulatory Text
| Document | Content |
|---|---|
| DFARS 225.7018 | Restrictions on acquisition of certain materials (tungsten, tantalum, etc.) |
| NDAA FY2024/2025 critical materials provisions | Legislative requirements and deadlines |
| DPA Title III award announcements | Specific awards with amounts, recipients, materials |

### Industry Sources
| Source | Content |
|---|---|
| Company 10-Ks and annual reports | Production capacity, supply chain disclosures |
| Company product pages (Kennametal, GTP, Elmet, HMI, 6K Additive, etc.) | Product capabilities, defense qualifications |
| Fastmarkets, Metal Bulletin | Price data, market analysis |
| Inside Government Contracts | Policy and procurement analysis |
| ITIA (International Tungsten Industry Association) | Tungsten market data |
| Nickel Institute | Nickel market data |

### Custom Analysis
| Document | Content |
|---|---|
| DoD Nickel and Tungsten Supply Chain Analysis (our HTML report) | Tiered supply chain mapping with cited data |

## 4. Technical Architecture

### 4.1 End-to-End Pipeline

```
                         ┌─────────────────────────────────┐
                         │         USER QUERY               │
                         └──────────────┬──────────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────────┐
                         │       QUERY CLASSIFIER            │
                         │  (rule-based + LLM fallback)      │
                         │                                   │
                         │  FACTUAL ─── RELATIONAL           │
                         │  REGULATORY ─ ANALYTICAL          │
                         │  COMPARATIVE                      │
                         └──────────────┬──────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                    │
                    ▼                   ▼                    ▼
         ┌──────────────┐   ┌──────────────┐    ┌──────────────┐
         │ VECTOR SEARCH │   │ BM25 SEARCH  │    │ GRAPH SEARCH │
         │  (pgvector)   │   │ (Supabase    │    │   (Neo4j)    │
         │  semantic     │   │  tsvector)   │    │  relational  │
         │  similarity   │   │  exact match │    │  traversal   │
         │  top-20       │   │  top-20      │    │              │
         └───────┬───────┘   └──────┬───────┘    └──────┬───────┘
                 │                  │                     │
                 └────────┬─────────┘                     │
                          ▼                               │
              ┌───────────────────────┐                   │
              │   RECIPROCAL RANK     │                   │
              │   FUSION (RRF)        │                   │
              │   merge vector + BM25 │                   │
              │   top-30 candidates   │                   │
              └───────────┬───────────┘                   │
                          │                               │
                          ▼                               │
              ┌───────────────────────┐                   │
              │   CROSS-ENCODER       │                   │
              │   RERANKER            │                   │
              │   ms-marco-MiniLM     │                   │
              │   top-30 → top-5-8    │                   │
              └───────────┬───────────┘                   │
                          │                               │
                          └──────────────┬────────────────┘
                                         │
                                         ▼
                          ┌──────────────────────────────┐
                          │   LLM GENERATION (Claude)     │
                          │                               │
                          │   Context: reranked chunks    │
                          │          + graph subgraph     │
                          │                               │
                          │   Prompt: answer with         │
                          │   [Source, Page] citations     │
                          └──────────────┬───────────────┘
                                         │
                                         ▼
                          ┌──────────────────────────────┐
                          │   SELF-CORRECTIVE VERIFIER    │
                          │                               │
                          │   Check: every citation real? │
                          │   Check: claims grounded?     │
                          │   Check: unsupported claims?  │
                          │                               │
                          │   PASS → return answer        │
                          │   FAIL → re-retrieve or       │
                          │          "insufficient data"  │
                          └──────────────────────────────┘
```

### 4.2 Document Ingestion Pipeline

```
Raw Document (PDF/HTML/TXT)
    ↓
Loader (pdfplumber / BeautifulSoup / unstructured)
    ↓
Section Parser (split by headings, tables, paragraphs)
    ↓
Chunker (500-1000 tokens, 100-token overlap, preserve metadata)
    ↓
┌──────────────────────────────────────────┐
│  In parallel:                            │
│  ├─ Embedder → pgvector                 │
│  ├─ Full-text indexer → tsvector         │
│  └─ Entity Extractor → JSON → Neo4j     │
└──────────────────────────────────────────┘
    ↓
Metadata Store (Supabase PostgreSQL)
```

#### Chunking Strategy
- **Primary split:** By document section headings (H1, H2, H3 for HTML; bold/font-size changes for PDF)
- **Secondary split:** If a section exceeds 1000 tokens, split at paragraph boundaries
- **Overlap:** 100 tokens between consecutive chunks from the same section
- **Metadata per chunk:**
  ```json
  {
    "chunk_id": "usgs_mcs_2026_nickel_003",
    "source_name": "USGS Mineral Commodity Summaries 2026",
    "source_url": "https://pubs.usgs.gov/periodicals/mcs2026/",
    "document_type": "usgs_mcs",
    "date_published": "2026-02-01",
    "materials": ["nickel"],
    "page_numbers": [132, 133],
    "section_title": "Nickel: Domestic Production and Use",
    "chunk_index": 3,
    "total_chunks_in_doc": 45,
    "text": "...",
    "embedding": [0.0123, ...]
  }
  ```

#### Entity Extraction
For each document, use an LLM call to extract structured entities:
```json
{
  "entities": [
    {
      "name": "Eagle Mine",
      "type": "Facility",
      "properties": {"location": "Michigan, USA", "operator": "Lundin Mining", "material": "Nickel", "capacity_mt_yr": 10000},
      "confidence": 0.95,
      "source_chunk_id": "usgs_mcs_2026_nickel_003",
      "verified": false
    }
  ],
  "relationships": [
    {
      "source": "Lundin Mining",
      "target": "Eagle Mine",
      "type": "OPERATES",
      "confidence": 0.95,
      "source_chunk_id": "usgs_mcs_2026_nickel_003",
      "verified": false
    }
  ]
}
```

Entities carry a `confidence` score (0-1) and a `verified` flag. Only `verified: true` or `confidence >= 0.85` entities are used in graph-based retrieval. Lower-confidence entities are stored but excluded from query results until manually reviewed.

### 4.3 Retrieval Strategy

#### Query Classification
| Query Type | Example | Retrieval Method |
|---|---|---|
| Factual | "What is U.S. nickel import reliance?" | Hybrid (vector + BM25) |
| Relational | "Who supplies tungsten to GD-OTS?" | Graph traversal + vector context |
| Analytical | "What happens if China cuts W exports?" | Graph traversal + hybrid retrieval |
| Regulatory | "When does the DFARS tungsten deadline hit?" | Hybrid, filtered to doc_type=regulatory |
| Comparative | "Compare nickel vs tungsten supply risk" | Multiple hybrid retrievals + synthesis |

#### Reciprocal Rank Fusion (RRF)
Merge vector and BM25 results using RRF scoring:
```
RRF_score(doc) = Σ 1 / (k + rank_in_list)
```
where k=60 (standard constant). Documents that appear in both result sets get boosted; documents that appear in only one still contribute. This is better than simple score normalization because it handles the different score distributions of vector cosine similarity vs BM25 naturally.

#### Cross-Encoder Reranking
After RRF merges the hybrid results (top 20-30 candidates), pass each (query, chunk_text) pair through a cross-encoder model that does full bidirectional attention. This produces a relevance score that is much more accurate than the initial retrieval scores.

Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Runs locally, no API calls
- ~50ms per candidate on CPU
- For 30 candidates: ~1.5 seconds total
- Keep top 5-8 candidates for the LLM

#### Graph-Based Retrieval
For relational queries, extract entity names from the query and run Cypher traversals:
```cypher
// "Who supplies tungsten to General Dynamics?"
MATCH path = (supplier)-[:PRODUCES|SUPPLIES_TO*1..3]->(target)
WHERE target.name =~ '(?i).*general dynamics.*'
AND ANY(node IN nodes(path) WHERE node.name =~ '(?i).*tungsten.*')
RETURN path
```

Graph results are converted to natural language context and appended to the reranked chunks before LLM generation.

### 4.4 Generation and Verification

#### Generation Prompt (system)
```
You are a critical materials supply chain analyst. Answer the user's question
using ONLY the provided context. Follow these rules strictly:

1. Every factual claim must cite its source in [brackets], e.g. [USGS MCS 2026, p.132]
2. If the context does not contain enough information to answer, say:
   "The available documents do not contain sufficient information to answer this question."
3. Never fabricate data, statistics, or source references
4. When citing numerical data, include the exact figure from the source
5. For relational answers (supply chains), describe the path:
   "Company A supplies Material X to Company B, which processes it into Product Y"
6. Distinguish between verified facts and estimates/approximations
```

#### Self-Corrective Verification
After generation, a second LLM call verifies the answer:

```
You are a fact-checker for critical materials supply chain analysis.
You will receive:
1. An ANSWER generated by another analyst
2. The SOURCE CONTEXT that was used to generate the answer

Evaluate the answer against these criteria:

CITATION CHECK: Does every [bracketed citation] correspond to actual content
in the source context? List any citations that do not match.

GROUNDING CHECK: Is every factual claim (numbers, dates, company names,
quantities) supported by the source context? List any ungrounded claims.

FABRICATION CHECK: Does the answer contain any information that does NOT
appear in the source context? List any fabricated content.

Respond with:
{
  "verdict": "PASS" | "FAIL",
  "issues": ["list of specific issues found"],
  "severity": "none" | "minor" | "major"
}

A PASS means all citations are real, all claims are grounded, and nothing
is fabricated. Any fabricated content is an automatic FAIL with major severity.
```

If verdict is FAIL with major severity: discard the answer, reformulate the query, re-retrieve, and try once more. If it fails again, return a "insufficient data" response rather than an unreliable answer.

If verdict is FAIL with minor severity (e.g., a slightly imprecise citation format): fix the minor issues and return.

### 4.5 Knowledge Graph Schema

#### Node Types
| Type | Properties | Example |
|---|---|---|
| Material | name, category, cas_number, criticality_level | Tungsten, Nickel |
| Company | name, headquarters, sector, ownership | Kennametal, GTP |
| Facility | name, location, type, capacity, status | Eagle Mine, GTP Towanda |
| WeaponSystem | name, platform_type, prime_contractor | F-35, M829A4 |
| Regulation | name, effective_date, scope, status | DFARS 225.7018 |
| Country | name, iso_code, alliance_status | China, Canada, South Korea |
| DPAAward | recipient, amount, material, date | 6K Additive $23.4M |
| StockpileItem | material, quantity, condition, action | Tungsten 2,041 mt acquisition |

#### Edge Types
| Type | From → To | Properties |
|---|---|---|
| MINES | Company/Facility → Material | capacity_mt_yr, ore_type |
| REFINES | Company/Facility → Material | process, purity, capacity |
| PRODUCES | Company → Material/Product | product_type, grade, capacity |
| SUPPLIES_TO | Company → Company | material, volume, contract_type |
| USED_IN | Material → WeaponSystem | component, quantity_per_unit, alloy |
| LOCATED_IN | Facility → Country | |
| OPERATES | Company → Facility | |
| RESTRICTS | Regulation → Material/Country | effective_date, scope |
| FUNDS | DPAAward → Company | amount, purpose |
| IMPORTS_FROM | Country → Country | material, volume, percentage |

### 4.6 API Design

```
POST /api/query
  Body: {
    "question": "...",
    "filters": {
      "materials": [...],
      "doc_types": [...],
      "date_after": "YYYY-MM-DD"
    },
    "include_graph": true,
    "include_sources": true
  }
  Response: {
    "answer": "...",
    "sources": [
      {"name": "...", "url": "...", "page": N, "section": "...", "relevance_score": 0.95}
    ],
    "graph_context": {
      "entities": [...],
      "relationships": [...]
    },
    "verification": {
      "verdict": "PASS",
      "issues": []
    },
    "metadata": {
      "query_type": "factual",
      "retrieval_method": "hybrid",
      "chunks_retrieved": 28,
      "chunks_after_rerank": 6,
      "latency_ms": 2340
    }
  }

POST /api/ingest
  Body: { "file_path": "...", "document_type": "...", "metadata": {...} }
  Response: { "chunks_created": N, "entities_extracted": N, "fts_indexed": true }

GET /api/graph/entity/{name}
  Response: { "entity": {...}, "relationships": [...] }

GET /api/graph/path?from=...&to=...
  Response: { "paths": [...] }

GET /api/documents
  Response: { "documents": [...] }

GET /api/health
  Response: { "status": "ok", "vector_count": N, "fts_count": N, "graph_nodes": N }
```

## 5. Database Schema (Supabase)

### documents table
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    source_url TEXT,
    document_type TEXT NOT NULL CHECK (document_type IN (
        'usgs_mcs', 'gao_report', 'crs_report', 'dpa_announcement',
        'industry', 'regulatory', 'custom_analysis', 'news'
    )),
    date_published DATE,
    materials TEXT[],
    file_path TEXT,
    file_hash TEXT,              -- SHA-256 hash for deduplication
    total_chunks INTEGER,
    ingested_at TIMESTAMPTZ DEFAULT now(),
    metadata JSONB
);

CREATE UNIQUE INDEX idx_documents_file_hash ON documents(file_hash);
```

### chunks table (with pgvector + full-text search)
```sql
CREATE EXTENSION IF NOT EXISTS vector;

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

-- Vector similarity index
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Full-text search index
CREATE INDEX idx_chunks_fts ON chunks USING gin (fts_vector);

-- Filter indexes
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_materials ON chunks USING gin (materials);
```

### extracted_entities table
```sql
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
```

### extracted_relationships table
```sql
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
```

### query_log table
```sql
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
```

## 6. Build Phases

### Phase 1: Foundation and Ingestion (Week 1-2)
- [ ] Initialize repo with project structure, pyproject.toml, .env.example
- [ ] Set up Supabase project with all tables (documents, chunks with pgvector + FTS, extracted_entities, extracted_relationships, query_log)
- [ ] Build document loader (PDF via pdfplumber, HTML via BeautifulSoup, plain text)
- [ ] Build section-aware chunker with metadata preservation
- [ ] Build embedder (OpenAI text-embedding-3-small, with batching and rate limit handling)
- [ ] Build full-text indexer (automatic via Supabase tsvector GENERATED column)
- [ ] Build ingestion pipeline orchestrator (loader → chunker → embed → store)
- [ ] Write ingestion CLI script with --source, --doc-type, --materials flags
- [ ] Ingest initial corpus: USGS MCS 2026, GAO reports, CRS reports
- [ ] Tests for loader, chunker, embedder
- [ ] Minimal README.md

### Phase 2: Hybrid RAG Chatbot (Week 2-4)
- [ ] Build vector retriever (pgvector cosine similarity)
- [ ] Build BM25 retriever (Supabase full-text search with ts_rank)
- [ ] Build hybrid retriever (RRF merging of vector + BM25 results)
- [ ] Build cross-encoder reranker (ms-marco-MiniLM-L-6-v2, local)
- [ ] Build query classifier (rule-based + LLM fallback)
- [ ] Build generation module with citation-enforcing prompts
- [ ] Build self-corrective verifier (CRAG pattern)
- [ ] Build end-to-end chain (classify → retrieve → rerank → generate → verify)
- [ ] Build FastAPI endpoints (/query, /health, /documents)
- [ ] Build Streamlit chatbot UI
- [ ] Test end-to-end with sample queries across all query types
- [ ] Deploy: API on Railway/Render, frontend on Streamlit Cloud
- [ ] Tests for all retrieval modules, reranker, verifier, generator

### Phase 3: Knowledge Graph (Week 4-6)
- [ ] Set up Neo4j AuraDB instance
- [ ] Define graph schema as Pydantic models (src/graph/schema.py)
- [ ] Create seed_data.json with manually curated nickel and tungsten supply chain data
- [ ] Build seed_graph.py script to load seed data into Neo4j
- [ ] Build LLM-based entity extractor with confidence scoring
- [ ] Build graph builder (extracted entities → Neo4j, respecting confidence thresholds)
- [ ] Build graph retriever (natural language → Cypher queries)
- [ ] Integrate graph retrieval into the hybrid pipeline (query classifier routes relational queries to graph)
- [ ] Update chatbot to display graph context alongside text answers
- [ ] Add entity extraction to the ingestion pipeline (optional flag: --extract-entities)
- [ ] Tests for entity extractor, graph retriever

### Phase 4: Polish and Scale (Week 6-8)
- [ ] Add more materials (rare earths, titanium, cobalt, lithium, copper)
- [ ] Ingest additional documents (company 10-Ks, DPA awards, NDAA text, DFARS)
- [ ] Build React frontend (replace or supplement Streamlit)
- [ ] Add query logging and analytics dashboard
- [ ] Add document management UI (upload, tag, re-ingest, view chunks)
- [ ] Write comprehensive README with architecture diagram, screenshots, demo
- [ ] Performance tuning (embedding cache, query result cache, batch reranking)
- [ ] Add metadata filters to query API (filter by material, doc_type, date range)

### Phase 5: Advanced Features (Week 8+)
- [ ] Scenario engine ("what if China cuts tungsten exports entirely")
- [ ] Regulatory timeline tracker with deadline alerts
- [ ] Automatic document monitoring (poll USGS, GAO for new publications)
- [ ] Integration with materials-priority-tool (link scoring data to supply chain intel)
- [ ] Multi-user access with Supabase auth and role-based permissions
- [ ] Export answers as formatted reports (PDF, DOCX)
- [ ] Feedback loop: use thumbs_up/thumbs_down to fine-tune retrieval and prompts

## 7. Seed Data for Knowledge Graph

The nickel and tungsten supply chain analysis we already completed provides the initial graph data. This is encoded as a JSON seed file (data/graph/seed_data.json) that the seed_graph.py script loads into Neo4j. All seed data is `verified: true`.

### Nickel Supply Chain (partial)
```
Lundin Mining --[OPERATES]--> Eagle Mine
Eagle Mine --[LOCATED_IN]--> USA
Eagle Mine --[MINES {capacity: 10000}]--> Nickel
Vale --[OPERATES]--> Sudbury Mines
Vale --[OPERATES]--> Long Harbour Refinery
Long Harbour Refinery --[REFINES]--> Nickel (Class I)
HMI (RTX) --[PRODUCES {grade: "UHP superalloy powder"}]--> Nickel Powder
Carpenter Technology --[PRODUCES]--> Nickel Powder
6K Additive --[PRODUCES]--> Nickel Powder
6K Additive --[FUNDED_BY {amount: 23400000}]--> DPA Title III
PCC --[PRODUCES]--> Nickel Superalloy Components
Pratt & Whitney --[INTEGRATES]--> F135 Engine
F135 Engine --[USED_IN]--> F-35
Nickel Superalloy --[USED_IN {qty_kg: 400}]--> F135 Engine
```

### Tungsten Supply Chain (partial)
```
China --[MINES {capacity: 67000, share: 0.80}]--> Tungsten
Almonty --[OPERATES]--> Sangdong Mine
Sangdong Mine --[LOCATED_IN]--> South Korea
GTP --[REFINES]--> Tungsten (APT, powder, WC)
GTP --[LOCATED_IN]--> USA (Towanda, PA)
Kennametal --[REFINES]--> Tungsten
Elmet Technologies --[PRODUCES]--> KEP Rods
General Dynamics OTS --[INTEGRATES]--> M829A4
M829A4 --[USED_IN]--> M1 Abrams
DFARS 225.7018 --[RESTRICTS {effective: "2027-01-01"}]--> Chinese Tungsten
Fireweed Metals --[FUNDED_BY {amount: 15800000}]--> DPA Title III
```

## 8. Why This Architecture (Decision Log)

### Why hybrid retrieval instead of vector-only?
Vector search alone misses exact terms. When a user asks about "GAO-24-107176" or "DFARS 225.7018", vector embeddings treat these as opaque strings and may retrieve semantically similar but wrong documents. BM25 catches exact matches. The combination via RRF outperforms either method alone in every published benchmark for factual Q&A.

### Why cross-encoder reranking?
Initial retrieval (vector or BM25) uses fast but approximate scoring. A cross-encoder does full bidirectional attention between the query and each candidate, producing much more accurate relevance scores. This is the single most impactful step for reducing hallucination, because the LLM only sees high-quality context.

### Why self-corrective verification (CRAG)?
In a defense/policy context, a wrong answer is worse than no answer. The verification step catches hallucinated citations, ungrounded claims, and fabricated data before they reach the user. The cost is one additional LLM call per query (roughly doubling the generation cost), which is negligible for a small team.

### Why not full Microsoft GraphRAG?
Microsoft's GraphRAG automatically builds communities and generates hierarchical summaries. This is designed for massive unstructured corpora (millions of documents) where manual curation is impossible. Our corpus is curated (50-100 high-quality documents), and our supply chain relationships are well-defined. A manually seeded + LLM-augmented graph with confidence thresholds gives us more reliable results with less complexity.

### Why not HyDE?
HyDE generates a hypothetical answer before retrieval. For our domain, a wrong hypothetical answer about defense supply chains could pull completely irrelevant context. The risk of amplifying errors outweighs the potential retrieval improvement.

### Why not ColBERT/late interaction?
ColBERT's token-level matching provides marginal precision gains over cross-encoder reranking, but adds significant infrastructure complexity (per-token index storage, custom retrieval server). At our document scale, the cross-encoder reranker achieves comparable precision with simpler infrastructure.

### Why Supabase for both vector and FTS?
Supabase natively supports pgvector (vector similarity) and tsvector (full-text search) in the same PostgreSQL database. This means hybrid retrieval requires no additional services, no data synchronization, and no extra cost. The alternative (separate Pinecone + Elasticsearch) adds complexity and cost with no quality benefit at our scale.
