<!-- From: C:\Users\PC\Desktop\auto-researcher\AGENTS.md -->
# AGENTS.md — Auto-Researcher MVP

## Project Overview

Auto-Researcher is a Python application that automatically ingests research papers from arXiv, classifies them into research buckets (General AI, Autonomous Agents, AI+Finance), and generates plain-English summaries via a local/cloud LLM (Ollama). It provides a FastAPI JSON API, a Click CLI for pipeline operations, and a React dashboard frontend. Vector embeddings are stored in **Pinecone Cloud** alongside SQLite metadata.

## Current Status: Fully Operational ✅

All five pipeline stages have been tested end-to-end with real data:

| Stage | Status | Verified |
|---|---|---|
| **Ingest** | ✅ Working | Papers fetched from 3 arXiv buckets, PDFs downloaded, text extracted |
| **Dedup** | ✅ Working | Fuzzy title matching removes duplicates, keeps longer content; orphans cleaned from Pinecone and FTS |
| **Classify** | ✅ Working | Hybrid RRF classification (dense cosine + BM25 via FTS5), borderline reranking, bucket embedding cache |
| **Report** | ✅ Working | Per-paper summaries (light model), per-bucket summaries + cross-domain synthesis (heavy model), LLM response cache, token cap |
| **API** | ✅ Working | All endpoints returning JSON |

## Tech Stack

- **Language:** Python 3.10+
- **Web Framework:** FastAPI + Uvicorn
- **Database:** SQLAlchemy with SQLite (`data/auto_researcher.db`)
- **Migrations:** Alembic (configured, initial migration present)
- **Full-Text Search:** SQLite FTS5 (BM25 keyword search)
- **Vector Database:** Pinecone Cloud (AWS Serverless, `us-east-1`) — `pinecone` SDK (unpinned)
- **LLM:** Ollama — `OLLAMA_MODEL` (heavy, default `gemma4:31b-cloud`), `OLLAMA_MODEL_LIGHT` (light, defaults to same), `nomic-embed-text-v2-moe` (embeddings)
- **LLM Orchestration:** LangChain (`langchain-ollama`)
- **PDF Processing:** pymupdf (fitz)
- **ML:** numpy (cosine similarity)
- **Fuzzy Matching:** rapidfuzz
- **CLI:** Click
- **Templating:** Jinja2
- **Data Source:** arxiv (Python arXiv API client, v2.1.3)
- **Alerting:** requests (webhook/Slack notifications)
- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui (Radix) + Recharts + Lucide + Marked

## Project Structure

```
auto-researcher/
├── run.py                  # CLI entry point (Click commands)
├── alembic.ini             # Alembic migration configuration
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .env                    # Local environment (gitignored)
├── data/
│   ├── pdfs/               # Downloaded PDFs (gitignored)
│   ├── llm_cache.json       # LLM response cache (gitignored)
│   ├── bucket_embeddings.json # Cached bucket description embeddings (auto-invalidated)
│   ├── auto_researcher.db  # SQLite database
│   └── reports/            # Generated reports (gitignored)
├── migrations/
│   ├── env.py              # Alembic environment config
│   └── versions/
│       └── 001_initial_schema.py  # Initial schema migration
├── tests/                  # Test suite
├── app/
│   ├── __init__.py
│   ├── config.py           # All settings from .env + bucket definitions
│   ├── database.py         # SQLAlchemy engine, session, Base, FTS5, context manager
│   ├── main.py             # FastAPI app factory (create_app)
│   ├── metrics.py          # Pipeline run tracking (duration, status, errors)
│   ├── alerts.py           # Webhook notification sender
│   ├── models/
│   │   ├── __init__.py
│   │   └── paper.py        # Paper, Report, PipelineRun SQLAlchemy models
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── arxiv_client.py # arXiv API search + keyword filtering + client-side date filter
│   │   ├── pdf_extractor.py # PDF download + text extraction
│   │   └── pipeline.py     # Orchestrates fetch → extract → store → FTS index update
│   ├── classification/
│   │   ├── __init__.py
│   │   ├── embedder.py     # Ollama embedding generation + dual-write (SQLite + Pinecone)
│   │   ├── classifier.py   # Hybrid RRF classification (dense cosine + BM25) with borderline reranking + auto-invalidating cache
│   │   ├── pinecone_store.py # Pinecone Cloud client: index management, upsert, query, delete, resync
│   │   └── dedup.py        # Fuzzy deduplication (rapidfuzz) + Pinecone/FTS orphan cleanup
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── generator.py    # LangChain + Ollama report generation (lazy LLM init + cache + cap + partial save)
│   │   └── prompts.py      # LLM prompt templates
│   └── dashboard/
│       ├── __init__.py
│       └── routes.py       # FastAPI JSON API endpoints (papers, stats, ingest, reports, search, pipeline-runs)
├── dashboard/              # React SPA frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── App.tsx           # Main shell with sidebar, search modal, nav
│   │   │   ├── data/api.ts       # API client layer (calls backend endpoints)
│   │   │   └── components/
│   │   │       ├── DashboardHome.tsx   # Stat cards, area chart, donut chart, recent papers
│   │   │       ├── PapersPanel.tsx     # Paper browser with bucket/text filters
│   │   │       ├── ReportsPanel.tsx    # Report generation, history, rich viewer, HTML export
│   │   │       ├── PipelinePanel.tsx   # Run history, stage breakdowns, duration chart
│   │   │       └── ui/               # 50+ shadcn/ui Radix components
│   │   ├── index.css
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── dist/               # Production build (served by FastAPI catch-all)
```

## CLI Commands

All commands run via `python run.py`:

| Command | Description |
|---|---|
| `python run.py ingest --max-results 2` | Fetch papers from arXiv, extract text, store in DB |
| `python run.py ingest --bucket general_ai` | Fetch papers from a single bucket only |
| `python run.py ingest --query "cat:cs.AI"` | Fetch with extra query filter (combined with bucket filters via AND) |
| `python run.py dedup` | Remove duplicate papers via fuzzy title matching + clean Pinecone/FTS orphans |
| `python run.py classify` | Embed and classify papers into buckets (requires Ollama + Pinecone) |
| `python run.py report --period 7d` | Generate report (periods: 7d, 1m, 3m, 6m, 1y) |
| `python run.py pipeline --period 7d` | Run full pipeline: ingest → dedup → embed → classify → report with metrics tracking |
| `python run.py pipeline --bucket general_ai --query "cat:cs.AI"` | Run pipeline targeting a specific bucket and/or query |
| `python run.py resync` | Re-sync embeddings from SQLite to Pinecone (recover from dual-write drift) |
| `python run.py serve [--host] [--port]` | Start dashboard server (default: 127.0.0.1:8000) |

## Dashboard Frontend

The React SPA is served by FastAPI in production via a catch-all `/{full_path:path}` route that falls back to `dashboard/dist/index.html`.

| Panel | Features |
|---|---|
| **Dashboard Home** | Stat cards (total papers, per-bucket counts), area chart (papers over time), donut chart (bucket distribution), recent papers list, latest pipeline runs |
| **Papers** | Bucket filter chips, client-side text search with highlight, expandable abstracts, arXiv external links, live paper count |
| **Reports** | Period selector (5 periods), report history list, rich report viewer modal with HTML export + print styles, markdown rendering via `marked` |
| **Pipeline** | Run history with expandable stage breakdowns, duration bar chart, "Run Pipeline" trigger button |
| **Global Search** | ⌘K / button-activated search modal calling `/search` with hybrid BM25 + vector search |

**CORS origins** (hardcoded in `app/main.py`): `https://ai-research-mvp.vercel.app`, `http://localhost:5173`

## Pipeline Flow

1. **Ingest** — Searches arXiv by category+keyword (sorted by relevance, filtered client-side for date), downloads PDFs, extracts text via pymupdf, stores in SQLite, populates FTS5 index. If PDF extraction fails, `full_text` is stored as an empty string (`""`) — the paper is still saved.
2. **Dedup** — O(n²) fuzzy title matching via `rapidfuzz.fuzz.ratio()`, removes duplicates keeping the paper with longer `full_text`. Also deletes orphan vectors from Pinecone and stale FTS rows.
3. **Classify** — Generates embeddings via `nomic-embed-text-v2-moe`, dual-writes to both SQLite and Pinecone. Uses **hybrid RRF classification**: dense cosine similarity against bucket embeddings + BM25 keyword search via FTS5, merged via Reciprocal Rank Fusion (`1/(k+dense_rank) + 1/(k+bm25_rank)`, default `k=60`). BM25 rankings are pre-computed per bucket. **Borderline reranking**: papers within `RERANK_MARGIN` (0.05) below the similarity threshold get re-scored using a weighted blend of cosine (0.6) and RRF (0.4). A borderline bucket is promoted only if the blended score is `>= SIMILARITY_THRESHOLD * 0.8` (i.e., 80% of the main threshold). Falls back to pure cosine if no BM25 results.
4. **Report** — Groups papers by bucket. Per-paper summaries use `llm_light` (lazy-initialized, configurable, defaults to `OLLAMA_MODEL`), per-bucket summaries + cross-domain synthesis use `llm_heavy` (`OLLAMA_MODEL`). LLM responses are cached to `data/llm_cache.json` keyed on SHA-256 hash of `model:prompt`. Token usage is tracked per run and capped by `OLLAMA_MAX_TOKENS_PER_RUN` (0 = unlimited). Partial results are saved on LLM failure — completed bucket summaries are preserved even if later buckets fail. **Note:** per-paper summaries are stored as a temporary `paper._summary` attribute in-memory; they are **not persisted** to the database.

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `https://ollama.com` | Ollama server URL (Cloud endpoint) |
| `OLLAMA_API_KEY` | *(empty)* | Ollama API key (required for Cloud) |
| `OLLAMA_MODEL` | `gemma4:31b-cloud` | LLM model for heavy tasks (bucket summaries, synthesis) |
| `OLLAMA_MODEL_LIGHT` | `gemma4:31b-cloud` | LLM model for light tasks (per-paper summaries). Defaults to `OLLAMA_MODEL`; change to a smaller model (e.g. `gemma3:4b`) for cost savings. |
| `OLLAMA_MAX_TOKENS_PER_RUN` | `0` | Max estimated tokens per report run (0 = unlimited) |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text-v2-moe` | Embedding model |
| `OLLAMA_EMBED_BASE_URL` | `http://localhost:11434` | **Separate endpoint for embeddings** (can differ from `OLLAMA_BASE_URL`) |
| `ARXIV_FROM_DATE` | `2020-01-01` | Only fetch papers published on or after this date (client-side filter) |
| `ARXIV_MAX_RESULTS` | `2` | Max papers per bucket |
| `SIMILARITY_THRESHOLD` | `0.35` | Min cosine similarity for bucket assignment |
| `RRF_K` | `60` | Reciprocal Rank Fusion constant |
| `RERANK_MARGIN` | `0.05` | Margin below similarity threshold for borderline re-scoring |
| `RERANK_WEIGHT_COSINE` | `0.6` | Weight for cosine score in rerank blend |
| `RERANK_WEIGHT_BM25` | `0.4` | Weight for BM25 RRF score in rerank blend |
| `DEDUP_THRESHOLD` | `0.85` | Min fuzzy score to consider duplicate |
| `PINECONE_API_KEY` | *(empty)* | Pinecone Cloud API key |
| `PINECONE_INDEX_NAME` | `auto-researcher-papers` | Pinecone index name |
| `PINECONE_EMBED_DIMENSION` | `768` | Embedding vector dimension (must match `OLLAMA_EMBED_MODEL`) |
| `APP_HOST` | `127.0.0.1` | Dashboard host |
| `APP_PORT` | `8000` | Dashboard port |
| `WEBHOOK_URL` | *(empty)* | Webhook URL for pipeline alerts (Slack-compatible). Empty = disabled |

## Database Models

- **Paper** (`papers` table): id, arxiv_id (unique), title (non-nullable Text), authors (nullable), abstract (nullable), full_text (nullable), pdf_url (nullable), published_date (nullable Date), ingested_at (nullable DateTime), buckets (nullable JSON string), embedding (nullable LargeBinary — also synced to Pinecone)
- **Report** (`reports` table): id, period (String 10), generated_at (DateTime), content_html (non-nullable Text), paper_count (non-nullable Integer)
- **PipelineRun** (`pipeline_runs` table): id, name (String 50), started_at (DateTime), finished_at (DateTime nullable), duration_s (Float nullable), status (String 20 — success/error/running), stages_json (Text nullable), error (Text nullable), paper_count (Integer nullable)
- **papers_fts** (FTS5 virtual table): rowid (= paper id), title, abstract — used for BM25 keyword search. Created by `init_db()`, populated on ingestion, cleaned on dedup, can be rebuilt via `rebuild_fts()`

### ⚠️ Migration/Model Mismatch Warning

The initial Alembic migration (`migrations/versions/001_initial_schema.py`) has **nullable and type mismatches** vs. the current SQLAlchemy models (`app/models/paper.py`):

| Table | Column | Model Definition | Migration Definition |
|---|---|---|---|
| `papers` | `title` | `Text`, `nullable=False` | `String`, `nullable=True` |
| `papers` | `authors` | `Text`, `nullable=True` | `String`, `nullable=True` |
| `papers` | `pdf_url` | `Text`, `nullable=True` | `String`, `nullable=True` |
| `papers` | `buckets` | `Text`, `nullable=True` | `String`, `nullable=True` |
| `reports` | `content_html` | `Text`, `nullable=False` | `Text`, `nullable=True` |
| `reports` | `paper_count` | `Integer`, `nullable=False` | `Integer`, `nullable=True` |

SQLite is permissive, so these mismatches do not cause runtime errors, but future migrations should align the schema with the models.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/papers` | Paginated paper listing with optional bucket filter (`?bucket=...&page=...&limit=...`) |
| GET | `/papers/stats` | Paper counts: total, per-bucket, and per-month (for dashboard charts) |
| POST | `/ingest` | Trigger ingestion → dedup → embed → classify. Returns JSON `{status, paper_count, stages}` |
| POST | `/reports/generate?period=7d` | Generate report. Returns JSON `{id, period, paper_count}` or `{error}` on failure |
| GET | `/search?q=...&limit=10` | Hybrid search: embed query, search Pinecone + FTS5, merge via RRF, return ranked JSON |
| GET | `/pipeline-runs` | List recent pipeline runs (JSON) |
| GET | `/reports` | List all reports (JSON array) |
| GET | `/reports/{id}` | Get single report (JSON). Returns 404 if not found |

## Code Conventions

- Config centralized in `app/config.py`; all settings read from `.env` via `python-dotenv`
- Database sessions use `get_session()` context manager from `app/database.py` for automatic cleanup (rollback on exception, close on exit). Legacy `Session()` factory still available for cases that need manual control (e.g., `metrics.py` which manages two sessions within a context manager, and `routes.py` which manually closes).
- **`track_pipeline(name)`** context manager in `app/metrics.py` records start/end time, status, errors, and stages to the `pipeline_runs` table. Yields a plain dict (`ctx`) for the caller to set `paper_count` and `stages_json`. Fires webhook alerts via `app/alerts.py` on completion.
- Logging uses `logging.getLogger(__name__)` — no print statements
- Embeddings serialized to bytes via `struct.pack` / deserialized via `struct.unpack` for SQLite; stored as float arrays in Pinecone
- Bucket assignments stored as JSON strings in the `buckets` column
- Pinecone client is a module-level singleton (`_pc_client` in `pinecone_store.py`) initialized eagerly at import time. All functions handle `None` client gracefully.
- CLI built with Click decorators in `run.py`; API routes in `app/dashboard/routes.py`
- LLM prompts stored as constants in `app/reports/prompts.py`
- Cosine similarity implemented in numpy (not scikit-learn)
- LLM calls use lazy-init tiered model routing: `_get_llm_light()` and `_get_llm_heavy()` create `OllamaLLM` instances on first use instead of at import time, avoiding crashes if Ollama is not yet running.
- LLM responses are cached to `data/llm_cache.json` keyed on SHA-256 hash of `model:prompt`. Cache is loaded once per `generate_report()` call and persists across runs. Token usage tracked via global `_tokens_used`, capped by `OLLAMA_MAX_TOKENS_PER_RUN` (0 = unlimited).
- `_cached_invoke()` has **3 retries with 2s backoff** on LLM failure. On final failure it logs and re-raises.
- Token counting is naive whitespace-split word count (`len(text.split())`) — not model-specific tokenization.
- Bucket description embeddings cached to `data/bucket_embeddings.json`. Cache is **auto-invalidated** via a SHA-256 fingerprint of `BUCKET_DESCRIPTIONS` — if the descriptions change, the cache is recomputed on next `classify` run. No manual file deletion needed.
- `embed_all_papers()` returns the count of successfully embedded papers (not the total queried). If Pinecone upsert fails, a warning is logged but the SQLite count is still accurate.
- `python run.py resync` re-syncs embeddings from SQLite to Pinecone — finds papers with embeddings in SQLite that are missing from Pinecone and upserts them. Used to recover from dual-write drift.
- FTS5 virtual table `papers_fts` used for BM25 keyword search during hybrid classification and the `/search` endpoint. Populated during ingestion, cleaned during dedup, rebuildable via `rebuild_fts()`.
- Pipeline metrics tracked in `pipeline_runs` table via `track_pipeline()` context manager. Webhook alerts sent after each run if `WEBHOOK_URL` is configured.
- Database migrations managed by Alembic. Run `alembic upgrade head` to apply migrations. Initial schema captured in `migrations/versions/001_initial_schema.py`.
- Report generation uses `Session()` factory (not `get_session()`) for safe session handling. Partial results (bucket summaries, cross-domain synthesis) are preserved on LLM failure.

## Known Issues

| Issue | Severity | Description |
|---|---|---|
| O(n²) deduplication | Medium | `dedup.py` compares every pair of papers. Will be slow for large databases. |
| API routes block synchronously | Medium | `POST /ingest` and `POST /reports/generate` block the server for the full pipeline duration with no user feedback. |
| `OLLAMA_MODEL_LIGHT` defaults to heavy model | Low | By default both light and heavy tasks use the same model (`gemma4:31b-cloud`). Cost savings only kick in when `OLLAMA_MODEL_LIGHT` is set to a smaller model in `.env`. |
| Migration/model mismatches | Low | Initial migration has nullable and type mismatches vs. models (see table above). SQLite is permissive so it does not break at runtime. |
| Frontend stale reference | Low | `dashboard/src/app/components/PapersPanel.tsx` line 171 references "Qdrant" but the backend uses Pinecone. |

## Testing

Tests live in `tests/`. Run with `python -m pytest tests/ -v`. The test suite uses `pytest` with in-memory SQLite and `unittest.mock` for all external services (Ollama, Pinecone, arXiv, HTTP).

### Test Structure

```
tests/
├── conftest.py               # Shared fixtures (DB, embeddings, paper factory)
├── test_arxiv_client.py       # matches_keywords, build_query
├── test_pdf_extractor.py       # download_pdf, extract_text
├── test_pipeline.py            # parse_published_date, run_ingestion
├── test_embedder.py            # embed_to_bytes, bytes_to_embed, get_embedding, embed_all_papers
├── test_classifier.py          # cosine_similarity, _sanitize_fts_query, classify_all_papers, compute_bucket_embeddings
├── test_dedup.py               # find_duplicates, deduplicate
├── test_generator.py           # format_papers, build_html_report, LLM cache, generate_report
├── test_metrics.py             # track_pipeline context manager
├── test_alerts.py              # send_alert
├── test_database.py            # init_db, get_session, rebuild_fts
└── test_routes.py              # FastAPI TestClient endpoints
```

### Key Testing Patterns

- **In-memory SQLite** (`sqlite:///:memory:`) with FTS5 for all DB-dependent tests
- **`unittest.mock.patch`** for all external services (Ollama, Pinecone, arXiv API, HTTP)
- **`conftest.py`** provides `db_session`, `make_paper`, `sample_embedding`, `sample_embedding_bytes` fixtures
- **`check_same_thread=False`** on SQLite engines used in route tests (FastAPI runs in threads)
- **Session isolation**: Tests that modify DB state use separate sessions; verify via raw SQL on engine connections when sessions may be closed

## Key Dependencies

```
fastapi==0.115.12, uvicorn==0.34.2    # Web framework
arxiv==2.1.3                          # arXiv API client
requests==2.32.3                       # HTTP downloads + webhook alerts
pymupdf==1.25.5                        # PDF text extraction
sqlalchemy==2.0.41, alembic==1.15.2    # Database + migrations
numpy==2.2.6                          # Numerical ops (cosine similarity)
langchain==0.3.25, langchain-ollama==0.3.3, ollama==0.5.1  # LLM integration
rapidfuzz==3.13.0                     # Fuzzy title matching
pinecone                              # Pinecone Cloud vector database (unpinned)
click==8.2.1                          # CLI
python-dotenv==1.1.0                  # Environment variables
tqdm==4.67.1                          # Progress bars
```

## Setup

```bash
python -m venv venv
venv\Scripts\activate              # Windows
pip install -r requirements.txt
cp .env.example .env              # Edit .env to add your OLLAMA_API_KEY and PINECONE_API_KEY
# Note: Since we are using Ollama Cloud, local model pulls via `ollama pull` are not required.
# Pinecone Cloud is used; no local Docker container is needed for the vector database.
python run.py serve                # Start API server on http://127.0.0.1:8000
```

## Database Migrations

```bash
# Apply pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description of change"
```

## arXiv API Quirks

The arXiv API returns **HTTP 500** when combining `submittedDate` range filters with `sortBy=SubmittedDate` on multi-category queries. To work around this:
- Queries use `sortBy=Relevance` (no date sorting)
- Date filtering is done client-side after fetching
- The client over-fetches (3× `max_results`) to compensate for papers filtered out by date
- `page_size=50`, `delay_seconds=5.0`, `num_retries=5` to avoid rate limiting (HTTP 429)
