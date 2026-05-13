# AGENTS.md — Auto-Researcher MVP

## Project Overview

Auto-Researcher is a Python application that automatically ingests research papers from arXiv, classifies them into research buckets (General AI, Autonomous Agents, AI+Finance), and generates plain-English summaries via a local/cloud LLM (Ollama). It provides a FastAPI web dashboard and a Click CLI for pipeline operations. Vector embeddings are stored in **Qdrant** (Docker) alongside SQLite metadata.

## Current Status: Fully Operational ✅

All five pipeline stages have been tested end-to-end with real data:

| Stage | Status | Verified |
|---|---|---|
| **Ingest** | ✅ Working | Papers fetched from 3 arXiv buckets, PDFs downloaded, text extracted |
| **Dedup** | ✅ Working | Fuzzy title matching removes duplicates, keeps longer content; orphans cleaned from Qdrant and FTS |
| **Classify** | ✅ Working | Hybrid RRF classification (dense cosine + BM25 via FTS5), borderline reranking, bucket embedding cache |
| **Report** | ✅ Working | Per-paper summaries (light model), per-bucket summaries + cross-domain synthesis (heavy model), LLM response cache, token cap |
| **Dashboard** | ✅ Working | All endpoints returning 200 |

## Tech Stack

- **Language:** Python 3.10+
- **Web Framework:** FastAPI + Uvicorn
- **Database:** SQLAlchemy with SQLite (`data/auto_researcher.db`)
- **Full-Text Search:** SQLite FTS5 (BM25 keyword search)
- **Vector Database:** Qdrant (Docker, `qdrant-client==1.18.0`)
- **LLM:** Ollama — `OLLAMA_MODEL` (heavy, default `gemma4:31b-cloud`), `OLLAMA_MODEL_LIGHT` (light, defaults to same), `nomic-embed-text-v2-moe` (embeddings)
- **LLM Orchestration:** LangChain (`langchain-ollama`)
- **PDF Processing:** pymupdf (fitz)
- **ML:** numpy (cosine similarity)
- **Fuzzy Matching:** rapidfuzz
- **CLI:** Click
- **Templating:** Jinja2
- **Data Source:** arxiv (Python arXiv API client, v2.1.3)
- **Alerting:** requests (webhook/Slack notifications)

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
│   ├── auto_researcher.db  # SQLite database
│   └── reports/            # Generated reports (gitignored)
├── tests/                  # Test suite (empty)
├── app/
│   ├── __init__.py
│   ├── config.py           # All settings from .env + bucket definitions
│   ├── database.py         # SQLAlchemy engine, session, Base, FTS5 index management
│   ├── main.py             # FastAPI app factory (create_app)
│   ├── metrics.py          # Pipeline run tracking (duration, status, errors)
│   ├── alerts.py            # Webhook notification sender
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
│   │   ├── embedder.py     # Ollama embedding generation + dual-write (SQLite + Qdrant)
│   │   ├── classifier.py   # Hybrid RRF classification (dense cosine + BM25) with borderline reranking
│   │   ├── qdrant_store.py # Qdrant client: collection management, upsert, search, delete
│   │   └── dedup.py        # Fuzzy deduplication (rapidfuzz) + Qdrant/FTS orphan cleanup
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── generator.py    # LangChain + Ollama report generation (tiered models + cache + cap)
│   │   └── prompts.py      # LLM prompt templates
│   └── dashboard/
│       ├── __init__.py
│       ├── routes.py        # FastAPI endpoints (dashboard, search, pipeline-runs, reports)
│       └── templates/       # HTML templates (base, dashboard, report, reports)
```

## CLI Commands

All commands run via `python run.py`:

| Command | Description |
|---|---|
| `python run.py ingest --max-results 2` | Fetch papers from arXiv, extract text, store in DB |
| `python run.py ingest --bucket general_ai` | Fetch papers from a single bucket only |
| `python run.py ingest --query "cat:cs.AI"` | Fetch with extra query filter (combined with bucket filters via AND) |
| `python run.py dedup` | Remove duplicate papers via fuzzy title matching + clean Qdrant/FTS orphans |
| `python run.py classify` | Embed and classify papers into buckets (requires Ollama + Qdrant) |
| `python run.py report --period 7d` | Generate report (periods: 7d, 6m, 1y) |
| `python run.py pipeline --period 7d` | Run full pipeline: ingest → dedup → embed → classify → report with metrics tracking |
| `python run.py serve [--host] [--port]` | Start dashboard server (default: 127.0.0.1:8000) |

## Pipeline Flow

1. **Ingest** — Searches arXiv by category+keyword (sorted by relevance, filtered client-side for date), downloads PDFs, extracts text via pymupdf, stores in SQLite, populates FTS5 index
2. **Dedup** — O(n²) fuzzy title matching via `rapidfuzz.fuzz.ratio()`, removes duplicates keeping the paper with longer `full_text`. Also deletes orphan vectors from Qdrant and stale FTS rows.
3. **Classify** — Generates embeddings via `nomic-embed-text-v2-moe` (cached to `data/bucket_embeddings.json`), dual-writes to both SQLite and Qdrant. Uses **hybrid RRF classification**: dense cosine similarity against bucket embeddings + BM25 keyword search via FTS5, merged via Reciprocal Rank Fusion (`1/(k+dense_rank) + 1/(k+bm25_rank)`, default `k=60`). BM25 rankings are pre-computed per bucket. **Borderline reranking**: papers within `RERANK_MARGIN` (0.05) below the similarity threshold get re-scored using a weighted blend of cosine (0.6) and RRF (0.4). Falls back to pure cosine if no BM25 results.
4. **Report** — Groups papers by bucket. Per-paper summaries use `llm_light` (configurable, defaults to `OLLAMA_MODEL`), per-bucket summaries + cross-domain synthesis use `llm_heavy` (`OLLAMA_MODEL`). LLM responses are cached to `data/llm_cache.json` keyed on SHA-256 hash of `model:prompt`. Token usage is tracked per run and capped by `OLLAMA_MAX_TOKENS_PER_RUN` (0 = unlimited).

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `gemma4:31b-cloud` | LLM model for heavy tasks (bucket summaries, synthesis) |
| `OLLAMA_MODEL_LIGHT` | `gemma4:31b-cloud` | LLM model for light tasks (per-paper summaries). Defaults to `OLLAMA_MODEL`; change to a smaller model (e.g. `gemma3:4b`) for cost savings. Requires `ollama pull`. |
| `OLLAMA_MAX_TOKENS_PER_RUN` | `0` | Max estimated tokens per report run (0 = unlimited) |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text-v2-moe` | Embedding model |
| `ARXIV_FROM_DATE` | `2020-01-01` | Only fetch papers published on or after this date (client-side filter) |
| `ARXIV_MAX_RESULTS` | `2` | Max papers per bucket |
| `SIMILARITY_THRESHOLD` | `0.35` | Min cosine similarity for bucket assignment |
| `RRF_K` | `60` | Reciprocal Rank Fusion constant |
| `RERANK_MARGIN` | `0.05` | Margin below similarity threshold for borderline re-scoring |
| `RERANK_WEIGHT_COSINE` | `0.6` | Weight for cosine score in rerank blend |
| `RERANK_WEIGHT_BM25` | `0.4` | Weight for BM25 RRF score in rerank blend |
| `DEDUP_THRESHOLD` | `0.85` | Min fuzzy score to consider duplicate |
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `QDRANT_PORT` | `6333` | Qdrant REST API port |
| `QDRANT_GRPC_PORT` | `6334` | Qdrant gRPC API port |
| `QDRANT_COLLECTION` | `papers` | Qdrant collection name |
| `QDRANT_EMBED_DIMENSION` | `768` | Embedding vector dimension (must match `OLLAMA_EMBED_MODEL`) |
| `APP_HOST` | `127.0.0.1` | Dashboard host |
| `APP_PORT` | `8000` | Dashboard port |
| `WEBHOOK_URL` | *(empty)* | Webhook URL for pipeline alerts (Slack-compatible). Empty = disabled |

## Database Models

- **Paper** (`papers` table): id, arxiv_id (unique), title, authors (nullable), abstract (nullable), full_text (nullable), pdf_url (nullable), published_date (nullable Date), ingested_at (nullable DateTime), buckets (nullable JSON string), embedding (nullable LargeBinary — also synced to Qdrant)
- **Report** (`reports` table): id, period (String 10), generated_at (DateTime), content_html (Text), paper_count (Integer)
- **PipelineRun** (`pipeline_runs` table): id, name (String 50), started_at (DateTime), finished_at (DateTime nullable), duration_s (Float nullable), status (String 20 — success/error/running), stages_json (Text nullable), error (Text nullable), paper_count (Integer nullable)
- **papers_fts** (FTS5 virtual table): rowid (= paper id), title, abstract — used for BM25 keyword search. Created by `init_db()`, populated on ingestion, cleaned on dedup, can be rebuilt via `rebuild_fts()`

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Dashboard home (paper counts, reports list, last pipeline run) |
| POST | `/ingest` | Trigger ingestion → dedup → embed → classify (with metrics tracking) |
| POST | `/reports/generate?period=7d` | Generate report (with metrics tracking) |
| GET | `/search?q=...&limit=10` | Hybrid search: embed query, search Qdrant + FTS5, merge via RRF, return ranked JSON |
| GET | `/pipeline-runs` | List recent pipeline runs (JSON) |
| GET | `/reports` | List all reports |
| GET | `/reports/{id}` | View single report |

## Code Conventions

- Config centralized in `app/config.py`; all settings read from `.env` via `python-dotenv`
- Database sessions use `Session()` from `app/database.py`; commit and close explicitly (no context managers — sessions can leak on exceptions)
- **`track_pipeline(name)`** context manager in `app/metrics.py` records start/end time, status, errors, and stages to the `pipeline_runs` table. Yields a plain dict (`ctx`) for the caller to set `paper_count` and `stages_json`. Fires webhook alerts via `app/alerts.py` on completion.
- Logging uses `logging.getLogger(__name__)` — no print statements
- Embeddings serialized to bytes via `struct.pack` / deserialized via `struct.unpack` for SQLite; stored as float arrays in Qdrant
- Bucket assignments stored as JSON strings in the `buckets` column
- Qdrant client is a module-level singleton (`_qdrant_client` in `qdrant_store.py`). All functions handle `None` client gracefully.
- CLI built with Click decorators in `run.py`; dashboard routes in `app/dashboard/routes.py`
- LLM prompts stored as constants in `app/reports/prompts.py`
- HTML templates use Jinja2 with a `base.html` layout
- Cosine similarity implemented in numpy (not scikit-learn)
- LLM calls use tiered model routing: `llm_light` (`OLLAMA_MODEL_LIGHT`) for per-paper summaries, `llm_heavy` (`OLLAMA_MODEL`) for bucket summaries and cross-domain synthesis. By default both use `gemma4:31b-cloud`; set `OLLAMA_MODEL_LIGHT` to a smaller model for cost savings.
- LLM responses are cached to `data/llm_cache.json` keyed on SHA-256 hash of `model:prompt`. Cache is loaded once per `generate_report()` call and persists across runs. Token usage tracked via global `_tokens_used`, capped by `OLLAMA_MAX_TOKENS_PER_RUN` (0 = unlimited).
- Bucket description embeddings cached to `data/bucket_embeddings.json`. Not invalidated on code change — delete manually if `BUCKET_DESCRIPTIONS` changes.
- FTS5 virtual table `papers_fts` used for BM25 keyword search during hybrid classification and the `/search` endpoint. Populated during ingestion, cleaned during dedup, rebuildable via `rebuild_fts()`.
- Pipeline metrics tracked in `pipeline_runs` table via `track_pipeline()` context manager. Webhook alerts sent after each run if `WEBHOOK_URL` is configured.

## Known Issues

| Issue | Severity | Description |
|---|---|---|
| O(n²) deduplication | Medium | `dedup.py` compares every pair of papers. Will be slow for large databases. |
| Dashboard routes block synchronously | Medium | `POST /ingest` and `POST /reports/generate` block the server for the full pipeline duration with no user feedback. |
| Unused dependencies | Low | `feedparser` and `dateparser` are in `requirements.txt` but never imported. |
| LLM instantiated at module level | Low | `generator.py` creates `OllamaLLM` instances at import time. No graceful fallback if Ollama is unavailable. |
| Bucket embedding cache staleness | Low | `data/bucket_embeddings.json` is never invalidated. If `BUCKET_DESCRIPTIONS` changes in code, the disk cache serves stale vectors. Delete the file manually. |
| Dual-write sync drift | Medium | If Qdrant upsert fails after SQLite commit, embeddings exist in SQLite but not Qdrant. `embed_all_papers()` skips them (already have `embedding != None`). Manual resync needed via a dedicated command. |
| Report period mismatch | Low | `run.py` CLI correctly offers only valid periods (`7d`, `6m`, `1y`), but `PERIOD_DAYS` in `generator.py` has no entries for `1m` or `3m`. Extend both if more periods are needed. |

## Testing

Tests live in `tests/` but are currently empty. When adding tests, use `pytest` and place test files matching `test_*.py` in the `tests/` directory.

## Key Dependencies

```
fastapi, uvicorn, jinja2          # Web framework + templates
arxiv==2.1.3                      # arXiv API client
requests                           # HTTP downloads + webhook alerts
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
ollama pull gemma4:31b-cloud      # Heavy LLM (bucket summaries, synthesis)
ollama pull nomic-embed-text-v2-moe # Embedding model (~957MB)
# Optional: pull a smaller model for cost savings on per-paper summaries:
# ollama pull gemma3:4b           # Then set OLLAMA_MODEL_LIGHT=gemma3:4b in .env
python run.py serve                # Start dashboard on http://127.0.0.1:8000
```

## arXiv API Quirks

The arXiv API returns **HTTP 500** when combining `submittedDate` range filters with `sortBy=SubmittedDate` on multi-category queries. To work around this:
- Queries use `sortBy=Relevance` (no date sorting)
- Date filtering is done client-side after fetching
- The client over-fetches (3× `max_results`) to compensate for papers filtered out by date
- `page_size=50`, `delay_seconds=5.0`, `num_retries=5` to avoid rate limiting (HTTP 429)