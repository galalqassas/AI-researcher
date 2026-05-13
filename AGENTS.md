# AGENTS.md — Auto-Researcher MVP

## Project Overview

Auto-Researcher is a Python application that automatically ingests research papers from arXiv, classifies them into research buckets (General AI, Autonomous Agents, AI+Finance), and generates plain-English summaries via a local/cloud LLM (Ollama). It provides a FastAPI web dashboard and a Click CLI for pipeline operations. Vector embeddings are stored in **Qdrant** (Docker) alongside SQLite metadata.

## Current Status: Fully Operational ✅

All five pipeline stages have been tested end-to-end with real data:

| Stage | Status | Verified |
|---|---|---|
| **Ingest** | ✅ Working | Papers fetched from 3 arXiv buckets, PDFs downloaded, text extracted |
| **Dedup** | ✅ Working | Fuzzy title matching removes duplicates, keeps longer content; orphans cleaned from Qdrant |
| **Classify** | ✅ Working | Embeddings via `nomic-embed-text-v2-moe`, stored in Qdrant, hybrid RRF classification (dense cosine + BM25 via FTS5) |
| **Report** | ✅ Working | Per-bucket + cross-domain synthesis via heavy model, per-paper summaries via light model, LLM responses cached |
| **Dashboard** | ✅ Working | All endpoints (GET `/`, `/reports`, `/reports/{id}`; POST `/ingest`, `/reports/generate`) returning 200 |

## Tech Stack

- **Language:** Python 3.10+
- **Web Framework:** FastAPI + Uvicorn
- **Database:** SQLAlchemy with SQLite (`data/auto_researcher.db`)
- **Vector Database:** Qdrant (Docker, `qdrant-client==1.18.0`)
- **LLM:** Ollama — `gemma4:31b-cloud` (heavy model, default for both), `OLLAMA_MODEL_LIGHT` (per-paper summaries, change to a smaller model for savings), `nomic-embed-text-v2-moe` (embeddings)
- **LLM Orchestration:** LangChain (`langchain-ollama`)
- **PDF Processing:** pymupdf (fitz)
- **ML:** numpy (cosine similarity)
- **Fuzzy Matching:** rapidfuzz
- **CLI:** Click
- **Templating:** Jinja2
- **Data Source:** arxiv (Python arXiv API client, v2.1.3)

## Project Structure

```
auto-researcher/
├── run.py                  # CLI entry point (Click commands)
├── docker-compose.yml      # Qdrant vector database service
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .env                    # Local environment (gitignored)
├── data/
│   ├── pdfs/               # Downloaded PDFs (gitignored)
│   ├── llm_cache.json       # LLM response cache (gitignored)
│   ├── bucket_embeddings.json # Cached bucket description embeddings (gitignored)
│   └── reports/            # Generated reports (gitignored)
├── migrations/             # Alembic migrations (empty, not configured)
├── tests/                  # Test suite (empty)
├── app/
│   ├── __init__.py
│   ├── config.py           # All settings from .env + bucket definitions
│   ├── database.py         # SQLAlchemy engine, session, Base, FTS5 index management
│   ├── main.py             # FastAPI app factory (create_app)
│   ├── models/
│   │   ├── __init__.py
│   │   └── paper.py        # Paper and Report SQLAlchemy models
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── arxiv_client.py # arXiv API search + keyword filtering + client-side date filter
│   │   ├── pdf_extractor.py # PDF download + text extraction
│   │   └── pipeline.py     # Orchestrates fetch → extract → store → FTS index update
│   ├── classification/
│   │   ├── __init__.py
│   │   ├── embedder.py     # Ollama embedding generation + dual-write (SQLite + Qdrant)
│   │   ├── classifier.py   # Hybrid RRF classification (dense cosine + BM25)
│   │   ├── qdrant_store.py # Qdrant client: collection management, upsert, search, delete
│   │   └── dedup.py        # Fuzzy deduplication (rapidfuzz) + Qdrant orphan cleanup
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── generator.py    # LangChain + Ollama report generation (tiered models + cache + cap)
│   │   └── prompts.py     # LLM prompt templates
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── routes.py       # FastAPI endpoints + Jinja2 rendering
│   │   └── templates/      # HTML templates (base, dashboard, report, reports)
│   └── cli/
│       └── __init__.py      # Empty (CLI lives in run.py)
```

## CLI Commands

All commands run via `python run.py`:

| Command | Description |
|---|---|
| `python run.py ingest --max-results 2` | Fetch papers from arXiv, extract text, store in DB |
| `python run.py ingest --query "cat:cs.AI"` | Fetch with extra query filter (combined with bucket filters via AND) |
| `python run.py dedup` | Remove duplicate papers via fuzzy title matching + clean Qdrant orphans |
| `python run.py classify` | Embed and classify papers into buckets (requires Ollama + Qdrant) |
| `python run.py report --period 7d` | Generate report (periods: 7d, 6m, 1y) |
| `python run.py serve [--host] [--port]` | Start dashboard server (default: 127.0.0.1:8000) |

**Note:** The `--query` flag does NOT replace bucket filters — it adds an additional AND clause. The full query becomes `bucket_categories AND bucket_keywords AND user_query`.

## Pipeline Flow

1. **Ingest** — Searches arXiv by category+keyword (sorted by relevance, filtered client-side for date), downloads PDFs, extracts text via pymupdf, stores in SQLite, populates FTS5 index
2. **Dedup** — O(n²) fuzzy title matching via `rapidfuzz.fuzz.ratio()`, removes duplicates keeping the paper with longer `full_text`. Also deletes orphan vectors from Qdrant.
3. **Classify** — Generates embeddings via `nomic-embed-text-v2-moe`, dual-writes to both SQLite (LargeBinary) and Qdrant. Uses **hybrid RRF classification**: dense cosine similarity ranked against bucket embeddings + BM25 keyword search via FTS5, merged via Reciprocal Rank Fusion (`1/(k+dense_rank) + 1/(k+bm25_rank)`, default `k=60`). Falls back to pure cosine if no BM25 results. Bucket description embeddings are cached to `data/bucket_embeddings.json`.
4. **Report** — Groups papers by bucket, generates per-paper summaries via the light model, per-bucket summaries (~500 words each) + cross-domain synthesis (~300 words) via the heavy model. LLM responses are cached to `data/llm_cache.json` keyed on prompt hash. Token usage is tracked per run and capped by `OLLAMA_MAX_TOKENS_PER_RUN` (0 = unlimited).

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `gemma4:31b-cloud` | LLM model for heavy tasks (bucket summaries, synthesis) |
| `OLLAMA_MODEL_LIGHT` | `gemma4:31b-cloud` | LLM model for light tasks (per-paper summaries). Defaults to same as OLLAMA_MODEL; change to a smaller model for cost savings |
| `OLLAMA_MAX_TOKENS_PER_RUN` | `0` | Max estimated tokens per report run (0 = unlimited) |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text-v2-moe` | Embedding model |
| `ARXIV_FROM_DATE` | `2020-01-01` | Only fetch papers published on or after this date (client-side filter) |
| `ARXIV_MAX_RESULTS` | `2` | Max papers per bucket |
| `SIMILARITY_THRESHOLD` | `0.35` | Min cosine similarity for bucket assignment |
| `RRF_K` | `60` | Reciprocal Rank Fusion constant for hybrid classification |
| `DEDUP_THRESHOLD` | `0.85` | Min fuzzy score to consider duplicate |
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `QDRANT_PORT` | `6333` | Qdrant REST API port |
| `QDRANT_GRPC_PORT` | `6334` | Qdrant gRPC API port |
| `QDRANT_COLLECTION` | `papers` | Qdrant collection name |
| `QDRANT_EMBED_DIMENSION` | `768` | Embedding vector dimension (must match `OLLAMA_EMBED_MODEL`) |
| `APP_HOST` | `127.0.0.1` | Dashboard host |
| `APP_PORT` | `8000` | Dashboard port |

## Database Models

- **Paper** (`papers` table): id, arxiv_id (unique), title, authors (nullable), abstract (nullable), full_text (nullable), pdf_url (nullable), published_date (nullable Date), ingested_at (nullable DateTime), buckets (nullable JSON string), embedding (nullable LargeBinary — also synced to Qdrant)
- **Report** (`reports` table): id, period (String 10), generated_at (DateTime), content_html (Text), paper_count (Integer)
- **papers_fts** (FTS5 virtual table): rowid (= paper id), title, abstract — used for BM25 keyword search in hybrid classification. Created automatically by `init_db()`, populated on ingestion, and can be rebuilt via `rebuild_fts()`

## Qdrant Vector Database

- Runs in Docker via `docker-compose.yml` (image: `qdrant/qdrant:latest`)
- Collection: `papers` (configurable via `QDRANT_COLLECTION`)
- Vector dimensions: 768 (configurable via `QDRANT_EMBED_DIMENSION`, default matches `nomic-embed-text-v2-moe`)
- Distance metric: Cosine
- Each point stores: paper ID (integer), vector (768-dim float), payload (`arxiv_id`, `title`, `model`)
- Client is a module-level singleton in `qdrant_store.py` with graceful fallback if Qdrant is unavailable
- Embeddings are dual-written (SQLite LargeBinary + Qdrant). Qdrant failures are logged but don't block the pipeline.

## Code Conventions

- Config centralized in `app/config.py`; all settings read from `.env` via `python-dotenv`
- Database sessions use `Session()` from `app/database.py`; commit and close explicitly (no context managers — sessions can leak on exceptions)
- Logging uses `logging.getLogger(__name__)` — no print statements
- Embeddings serialized to bytes via `struct.pack` / deserialized via `struct.unpack` for SQLite; stored as float arrays in Qdrant
- Bucket assignments stored as JSON strings in the `buckets` column
- Qdrant client is a module-level singleton (`_qdrant_client` in `qdrant_store.py`). All functions handle `None` client gracefully.
- CLI built with Click decorators in `run.py`; dashboard routes in `app/dashboard/routes.py`
- LLM prompts stored as constants in `app/reports/prompts.py`
- HTML templates use Jinja2 with a `base.html` layout
- Cosine similarity implemented in numpy (not scikit-learn — the dependency is unused)
- LLM calls use tiered model routing: `llm_light` (`OLLAMA_MODEL_LIGHT`) for per-paper summaries, `llm_heavy` (`OLLAMA_MODEL`) for bucket summaries and cross-domain synthesis. By default both use `gemma4:31b-cloud`; set `OLLAMA_MODEL_LIGHT` to a smaller model (e.g. `gemma3:4b`) for cost savings
- LLM responses are cached to `data/llm_cache.json` keyed on SHA-256 hash of `model:prompt`. Cache persists across runs. Token usage is tracked per run via global `_tokens_used` and capped by `OLLAMA_MAX_TOKENS_PER_RUN` (0 = unlimited).
- Token estimation uses `len(text.split())` — a rough approximation, not exact tokenization
- Bucket description embeddings are cached to `data/bucket_embeddings.json` to avoid recomputing on each classification run
- FTS5 virtual table `papers_fts` is used for BM25 keyword search during hybrid classification. It is populated during ingestion and can be rebuilt via `rebuild_fts()` in `database.py`.

## Known Issues

| Issue | Severity | Description |
|---|---|---|
| O(n²) deduplication | Medium | `dedup.py` compares every pair of papers. Will be slow for large databases. |
| Dashboard routes block synchronously | Medium | `POST /ingest` and `POST /reports/generate` block the server for the full pipeline duration with no user feedback. |
| Unused dependencies | Low | `feedparser` and `dateparser` are in `requirements.txt` but never imported. |
| LLM instantiated at module level | Low | `generator.py` creates `OllamaLLM` instances at import time. No graceful fallback if Ollama is unavailable. |
| Report period mismatch | Medium | `run.py` CLI offers 5 periods (`7d, 1m, 3m, 6m, 1y`) but `generate_report()` only accepts 3 (`7d, 6m, 1y` per `REPORT_PERIODS`). Selecting `1m` or `3m` raises `ValueError`. **Note:** CLI was fixed to only offer valid periods, but `PERIOD_DAYS` in `generator.py` has no entries for `1m`/`3m` either — extend both if more periods are needed. |
| FTS index can drift | Low | Dedup now cleans FTS rows, but direct DB edits bypass FTS. `rebuild_fts()` in `database.py` can manually rebuild if drift occurs. |
| Bucket embedding cache staleness | Low | `data/bucket_embeddings.json` is never invalidated. If `BUCKET_DESCRIPTIONS` changes in code, the disk cache serves stale vectors. Delete the file manually or add a hash check. |
| Dual-write sync drift | Medium | If Qdrant upsert fails after SQLite commit, embeddings exist in SQLite but not Qdrant. Next `embed_all_papers()` skips them (they already have `embedding != None`). Manual resync needed via a `qdrant_sync` command (not yet implemented). |

## Testing

Tests live in `tests/` but are currently empty. When adding tests, use `pytest` and place test files matching `test_*.py` in the `tests/` directory.

## Key Dependencies

```
fastapi, uvicorn, jinja2          # Web framework + templates
arxiv==2.1.3                      # arXiv API client (v2.1.5 doesn't exist)
requests                           # HTTP downloads
pymupdf                            # PDF text extraction
sqlalchemy, alembic                # Database + migrations (alembic not configured)
numpy                              # Numerical ops (cosine similarity)
langchain, langchain-ollama, ollama # LLM integration
rapidfuzz                          # Fuzzy title matching
qdrant-client==1.18.0              # Vector database client
click                              # CLI
python-dotenv                      # Environment variables
tqdm                               # Progress bars
```

## Setup

```bash
python -m venv venv
venv\Scripts\activate              # Windows
pip install -r requirements.txt
cp .env.example .env              # Edit .env if needed
docker compose up -d              # Start Qdrant vector database
ollama pull gemma4:31b-cloud      # LLM for bucket summaries and synthesis
# To enable cost savings, also pull a smaller model and set OLLAMA_MODEL_LIGHT:
# ollama pull gemma3:4b           # Lighter LLM for per-paper summaries
ollama pull nomic-embed-text-v2-moe # Embedding model (~957MB)
python run.py serve                # Start dashboard on http://127.0.0.1:8000
```

## Dashboard Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Dashboard home (paper counts, reports list) |
| POST | `/ingest` | Trigger ingestion → dedup → embed (SQLite + Qdrant) → classify, redirect to `/` |
| POST | `/reports/generate?period=7d` | Generate report, redirect to report page |
| GET | `/reports` | List all reports |
| GET | `/reports/{id}` | View single report |

**Note:** `POST /ingest` now runs the full pipeline: ingest → dedup → embed (dual-write to SQLite + Qdrant) → classify.

## arXiv API Quirks

The arXiv API returns **HTTP 500** when combining `submittedDate` range filters with `sortBy=SubmittedDate` on multi-category queries. To work around this:
- Queries use `sortBy=Relevance` (no date sorting)
- Date filtering is done client-side after fetching
- The client over-fetches (3× `max_results`) to compensate for papers filtered out by date
- `page_size=50`, `delay_seconds=5.0`, `num_retries=5` to avoid rate limiting (HTTP 429)