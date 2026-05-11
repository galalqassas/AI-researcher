# Auto-Researcher MVP

Automatically ingests research papers from arXiv, classifies them into research buckets (General AI, Autonomous Agents, AI+Finance), and generates plain-English summaries via a local LLM.

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) running locally with models pulled:
  ```
  ollama pull gemma4:31b-cloud
  ollama pull nomic-embed-text-v2-moe
  ```

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Edit .env if needed
```

## Usage

### CLI Commands

```bash
# 1. Fetch papers from arXiv
python run.py ingest --max-results 50

# 2. Remove duplicates
python run.py dedup

# 3. Embed and classify papers (requires Ollama)
python run.py classify

# 4. Generate a report
python run.py report --period 7d

# 5. Start dashboard
python run.py serve
```

### Dashboard

Open http://127.0.0.1:8000 after running `python run.py serve`.

The dashboard shows paper counts, lets you trigger ingestion, and generate reports for 7 days / 1 month / 3 months / 6 months / 1 year.

## How It Works

1. **Ingestion** — Searches arXiv by category (cs.AI, cs.LG, q-fin, etc.) then filters by keywords. Downloads PDFs and extracts full text using pymupdf.
2. **Deduplication** — Uses fuzzy title matching (rapidfuzz) to remove near-duplicate papers.
3. **Classification** — Generates embeddings via Ollama (nomic-embed-text-v2-moe), then computes cosine similarity against each bucket description. Papers can belong to multiple buckets.
4. **Report Generation** — groups papers by bucket, sends each group to Ollama (gemma4:31b-cloud) for a plain-English summary, then synthesizes cross-bucket insights.

## Architecture

```
app/
├── config.py              # All settings from .env
├── database.py            # SQLAlchemy + SQLite
├── main.py                # FastAPI app factory
├── models/paper.py         # Paper + Report tables
├── ingestion/
│   ├── arxiv_client.py    # arXiv API search
│   ├── pdf_extractor.py   # PDF download + text extraction
│   └── pipeline.py        # Orchestrates fetch → store
├── classification/
│   ├── embedder.py        # Ollama embeddings
│   ├── classifier.py      # Bucket assignment
│   └── dedup.py           # Fuzzy deduplication
├── reports/
│   ├── generator.py       # LangChain + Ollama reports
│   └── prompts.py          # LLM prompt templates
└── dashboard/
    ├── routes.py           # FastAPI endpoints
    └── templates/          # HTML templates
```

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | http://localhost:11434 | Ollama server URL |
| `OLLAMA_MODEL` | gemma4:31b-cloud | LLM model for reports |
| `OLLAMA_EMBED_MODEL` | nomic-embed-text-v2-moe | Embedding model |
| `ARXIV_FROM_DATE` | 2020-01-01 | Only fetch papers from this date |
| `ARXIV_MAX_RESULTS` | 50 | Max papers per bucket |
| `SIMILARITY_THRESHOLD` | 0.35 | Min cosine similarity for bucket assignment |
| `DEDUP_THRESHOLD` | 0.85 | Min fuzzy score to consider a duplicate |