# Auto-Researcher MVP

Automatically ingests research papers from arXiv, classifies them into research buckets (General AI, Autonomous Agents, AI+Finance), and generates plain-English summaries via a local LLM (Ollama).

## Prerequisites

| Tool | Required Version | Notes |
|---|---|---|
| **Python** | 3.10+ | Used for backend pipeline and API |
| **Node.js** | 18+ | Used for dashboard frontend (React + Vite) |
| **pnpm** | Any | Dashboard package manager (lockfile present) |
| **Docker** | Any modern version | For Pinecone vector database |
| **Ollama** | Latest | Must be running locally with models pulled |

## Dependencies

### Python (`requirements.txt`)

```
fastapi==0.115.12        uvicorn==0.34.2          jinja2==3.1.6
arxiv==2.1.3             requests==2.32.3         pymupdf==1.25.5
sqlalchemy==2.0.41       alembic==1.15.2          numpy==2.2.6
langchain==0.3.25        langchain-ollama==0.3.3  ollama==0.5.1
rapidfuzz==3.13.0        python-dotenv==1.1.0     click==8.2.1
tqdm==4.67.1             pinecone-client==1.18.0
```

### Frontend (`dashboard/package.json`)

- **Build Tool:** Vite 6.3.5
- **Framework:** React 18.3.1 + TypeScript
- **Styling:** Tailwind CSS v4 + shadcn/ui Radix primitives
- **Charts:** Recharts 2.15.2
- **Routing:** React Router 7.13.0
- **Icons:** lucide-react 0.487.0

## Environment Variables

Create `.env` by copying `.env.example`:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `gemma4:31b-cloud` | Heavy LLM for bucket summaries, synthesis |
| `OLLAMA_MODEL_LIGHT` | `gemma4:31b-cloud` | Light LLM for per-paper summaries. Set to a smaller model (e.g. `gemma3:4b`) for cost savings |
| `OLLAMA_MAX_TOKENS_PER_RUN` | `0` | Max tokens per report run. `0` = unlimited |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text-v2-moe` | Embedding model (~957MB) |
| `ARXIV_FROM_DATE` | `2020-01-01` | Only fetch papers on or after this date |
| `ARXIV_MAX_RESULTS` | `2` | Max papers per bucket |
| `SIMILARITY_THRESHOLD` | `0.35` | Min cosine similarity for bucket assignment |
| `RRF_K` | `60` | Reciprocal Rank Fusion constant |
| `RERANK_MARGIN` | `0.05` | Margin below threshold for borderline re-scoring |
| `RERANK_WEIGHT_COSINE` | `0.6` | Cosine weight in rerank blend |
| `RERANK_WEIGHT_BM25` | `0.4` | BM25 weight in rerank blend |
| `DEDUP_THRESHOLD` | `0.85` | Min fuzzy score to consider a duplicate |
| `QDRANT_HOST` | `localhost` | Pinecone server host |
| `QDRANT_PORT` | `6333` | Pinecone REST API port |
| `QDRANT_GRPC_PORT` | `6334` | Pinecone gRPC API port |
| `QDRANT_COLLECTION` | `papers` | Pinecone collection name |
| `QDRANT_EMBED_DIMENSION` | `768` | Embedding vector dimension |
| `APP_HOST` | `127.0.0.1` | Dashboard host |
| `APP_PORT` | `8000` | Dashboard port |
| `WEBHOOK_URL` | *(empty)* | Slack-compatible webhook for alerts. Empty = disabled |

## Setup

### 1. Backend & Services

```bash
# Clone repository
git clone <repo-url>
cd auto-researcher

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env if needed

# Start Pinecone
docker compose up -d

# Pull Ollama models
ollama pull gemma4:31b-cloud
ollama pull nomic-embed-text-v2-moe
# Optional: pull smaller light model
# ollama pull gemma3:4b
```

### 2. Frontend

```bash
cd dashboard
pnpm install
pnpm build
cd ..
```

## Running the Application

```bash
# Run the full pipeline
python run.py pipeline --period 7d

# Or run stages individually:
python run.py ingest --max-results 10
python run.py dedup
python run.py classify
python run.py report --period 7d

# Start API server + dashboard
python run.py serve
# Open http://127.0.0.1:8000
```

### Frontend Development Server

```bash
cd dashboard
pnpm dev
# Opens on http://localhost:5173 (proxies API to :8000)
```

## Running Tests

```bash
# From project root, with venv activated
python -m pytest tests/ -v
```

Tests use in-memory SQLite with FTS5 and mock all external services (Ollama, Pinecone, arXiv, HTTP).

## Project Structure

```
auto-researcher/
├── run.py                  # CLI entry point (Click commands)
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── docker-compose.yml      # Pinecone vector database
├── alembic.ini             # Alembic migration config
├── data/                   # Runtime data (DB, PDFs, reports, cache)
├── migrations/             # Alembic migrations
├── tests/                  # Pytest test suite
├── app/
│   ├── config.py           # All settings from .env + bucket definitions
│   ├── database.py         # SQLAlchemy engine, session, Base, FTS5
│   ├── main.py             # FastAPI app factory
│   ├── models/paper.py     # Paper, Report, PipelineRun models
│   ├── ingestion/          # arXiv fetch + PDF text extraction
│   ├── classification/     # Embeddings + classification + dedup + Pinecone
│   ├── reports/            # LLM report generation
│   └── dashboard/routes.py # FastAPI API endpoints
└── dashboard/
    ├── package.json        # Frontend dependencies
    ├── vite.config.ts      # Vite config + API proxy
    └── src/                # React source components
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/ingest` | Trigger full pipeline ingestion |
| POST | `/reports/generate?period=7d` | Generate report |
| GET | `/search?q=...&limit=10` | Hybrid semantic + keyword search |
| GET | `/pipeline-runs` | List pipeline runs |
| GET | `/reports` | List all reports |
| GET | `/reports/{id}` | Get single report |

## Pipeline Flow

1. **Ingest** — Searches arXiv by category+keyword, downloads PDFs, extracts text (pymupdf), stores in SQLite, populates FTS5
2. **Dedup** — O(n²) fuzzy title matching (rapidfuzz) removes duplicates, cleans Pinecone/FTS orphans
3. **Classify** — Generates embeddings (`nomic-embed-text-v2-moe`), dual-writes to SQLite+Pinecone. Hybrid RRF classification: dense cosine + BM25 via FTS5
4. **Report** — Groups papers by bucket. Per-paper summaries (light model), per-bucket summaries + cross-domain synthesis (heavy model). LLM cache + token cap

## Database Migrations

```bash
# Apply pending migrations
alembic upgrade head

# Create new migration after model changes
alembic revision --autogenerate -m "description of change"
```

## Architecture Decisions

| Decision | Detail |
|---|---|
| **Database** | SQLite (`data/auto_researcher.db`) with FTS5 for BM25 keyword search |
| **Vector DB** | Pinecone via Docker, dual-writes with SQLite |
| **Embeddings** | 768-dim from `nomic-embed-text-v2-moe` via Ollama |
| **LLM Routing** | Lazy-init: `_get_llm_light()` and `_get_llm_heavy()` |
| **LLM Caching** | SHA-256 keyed responses to `data/llm_cache.json` |
| **Deduplication** | O(n²) fuzzy title matching via rapidfuzz |

## Platform Notes

### Windows
- Activate venv with `venv\Scripts\activate`
- Developed and tested on Windows

### arXiv API Quirks
- Returns HTTP 500 when combining `submittedDate` with `sortBy=SubmittedDate` on multi-category queries
- Uses `sortBy=Relevance` + client-side date filtering as workaround
- Over-fetches 3× `max_results` and uses `page_size=50`, `delay_seconds=5.0`, `num_retries=5` for rate limiting

## Gitignore (Runtime Files)

These are generated at runtime and should **not** be committed:
- `data/pdfs/`, `data/reports/`, `data/llm_cache.json`, `data/bucket_embeddings.json`
- `data/auto_researcher.db`
- `dashboard/dist/`, `dashboard/node_modules/`

## License

MIT
