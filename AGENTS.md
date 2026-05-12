# AGENTS.md — Auto-Researcher MVP

## Project Overview

Auto-Researcher is a Python application that automatically ingests research papers from arXiv, classifies them into research buckets (General AI, Autonomous Agents, AI+Finance), and generates plain-English summaries via a local/cloud LLM (Ollama). It provides a FastAPI web dashboard and a Click CLI for pipeline operations. Vector embeddings are stored in **Qdrant** (Docker) alongside SQLite metadata.

## Current Status: Fully Operational ✅

All five pipeline stages have been tested end-to-end with real data:

| Stage | Status | Verified |
|---|---|---|
| **Ingest** | ✅ Working | Papers fetched from 3 arXiv buckets, PDFs downloaded, text extracted |
| **Dedup** | ✅ Working | Fuzzy title matching removes duplicates, keeps longer content; orphans cleaned from Qdrant |
| **Classify** | ✅ Working | Embeddings via `nomic-embed-text-v2-moe`, stored in Qdrant, cosine similarity bucket assignment |
| **Report** | ✅ Working | Per-bucket summaries + cross-domain synthesis via `gemma4:31b-cloud` |
| **Dashboard** | ✅ Working | All endpoints (GET `/`, `/reports`, `/reports/{id}`; POST `/ingest`, `/reports/generate`) returning 200 |

## Tech Stack

- **Language:** Python 3.10+
- **Web Framework:** FastAPI + Uvicorn
- **Database:** SQLAlchemy with SQLite (`data/auto_researcher.db`)
- **Vector Database:** Qdrant (Docker, `qdrant-client==1.18.0`)
- **LLM:** Ollama — `gemma4:31b-cloud` (reports), `nomic-embed-text-v2-moe` (embeddings)
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
│   └── reports/            # Generated reports (gitignored)
├── migrations/             # Alembic migrations (empty, not configured)
├── tests/                  # Test suite (empty)
├── app/
│   ├── __init__.py
│   ├── config.py           # All settings from .env + bucket definitions
│   ├── database.py         # SQLAlchemy engine, session, Base
│   ├── main.py             # FastAPI app factory (create_app)
│   ├── models/
│   │   ├── __init__.py
│   │   └── paper.py        # Paper and Report SQLAlchemy models
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── arxiv_client.py # arXiv API search + keyword filtering + client-side date filter
│   │   ├── pdf_extractor.py # PDF download + text extraction
│   │   └── pipeline.py     # Orchestrates fetch → extract → store
│   ├── classification/
│   │   ├── __init__.py
│   │   ├── embedder.py     # Ollama embedding generation + dual-write (SQLite + Qdrant)
│   │   ├── classifier.py   # Bucket assignment via cosine similarity
│   │   ├── qdrant_store.py # Qdrant client: collection management, upsert, search, delete
│   │   └── dedup.py        # Fuzzy deduplication (rapidfuzz) + Qdrant orphan cleanup
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── generator.py    # LangChain + Ollama report generation
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
| `python run.py report --period 7d` | Generate report (periods: 7d, 1m, 3m, 6m, 1y) |
| `python run.py serve [--host] [--port]` | Start dashboard server (default: 127.0.0.1:8000) |

**Note:** The `--query` flag does NOT replace bucket filters — it adds an additional AND clause. The full query becomes `bucket_categories AND bucket_keywords AND user_query`.

## Pipeline Flow

1. **Ingest** — Searches arXiv by category+keyword (sorted by relevance, filtered client-side for date), downloads PDFs, extracts text via pymupdf, stores in SQLite
2. **Dedup** — O(n²) fuzzy title matching via `rapidfuzz.fuzz.ratio()`, removes duplicates keeping the paper with longer `full_text`. Also deletes orphan vectors from Qdrant.
3. **Classify** — Generates embeddings via `nomic-embed-text-v2-moe`, dual-writes to both SQLite (LargeBinary) and Qdrant. Computes cosine similarity against bucket descriptions, assigns papers to matching buckets (threshold ≥ 0.35). Papers with no bucket above threshold fall back to the single highest-scoring bucket.
4. **Report** — Groups papers by bucket, generates per-bucket summaries (~500 words each) + cross-domain synthesis (~300 words) via `gemma4:31b-cloud`, stores HTML report in DB. Does NOT use Qdrant — reads paper metadata from SQLite only.

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `gemma4:31b-cloud` | LLM model for reports |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text-v2-moe` | Embedding model |
| `ARXIV_FROM_DATE` | `2020-01-01` | Only fetch papers published on or after this date (client-side filter) |
| `ARXIV_MAX_RESULTS` | `2` | Max papers per bucket |
| `SIMILARITY_THRESHOLD` | `0.35` | Min cosine similarity for bucket assignment |
| `DEDUP_THRESHOLD` | `0.85` | Min fuzzy score to consider duplicate. **⚠ Note:** `.env` and `.env.example` name this `DEDUP_SIMILARITY_THRESHOLD`, but the code reads `DEDUP_THRESHOLD`. The `.env` value is currently ignored; the default `0.85` is always used. |
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

## Known Issues

| Issue | Severity | Description |
|---|---|---|
| `.env` variable name mismatch | Medium | `.env` defines `DEDUP_SIMILARITY_THRESHOLD` but `config.py` reads `DEDUP_THRESHOLD`. The `.env` value is silently ignored; default `0.85` is always used. |
| `run_ingestion` returns `None` | Low | When no papers are fetched, `pipeline.py` returns bare `return` (yields `None` instead of `0`). `run.py` prints `"Ingestion complete: None new papers stored"`. |
| `Report.generated_at` type annotation | Low | Annotated as `Mapped[str]` but column is `DateTime`. Should be `Mapped[datetime]`. |
| `datetime.utcnow()` deprecated | Low | Used in `pipeline.py`, `generator.py`, `routes.py`. Should use `datetime.now(timezone.utc)` for Python 3.12+. |
| O(n²) deduplication | Medium | `dedup.py` compares every pair of papers. Will be slow for large databases. |
| Dashboard routes block synchronously | Medium | `POST /ingest` and `POST /reports/generate` block the server for the full pipeline duration with no user feedback. |
| Unused dependencies | Low | `feedparser` and `dateparser` are in `requirements.txt` but never imported. |
| LLM instantiated at module level | Low | `generator.py` creates `OllamaLLM(model=OLLAMA_MODEL)` at import time. No graceful fallback if Ollama is unavailable. |
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
ollama pull gemma4:31b-cloud      # LLM for report generation
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