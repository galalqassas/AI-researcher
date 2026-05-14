import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PDFS_DIR = DATA_DIR / "pdfs"
REPORTS_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "auto_researcher.db"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
# OLLAMA_MODEL_LIGHT: defaults to OLLAMA_MODEL (same model). Set to a smaller model
# (e.g. gemma3:4b) for cost savings on per-paper summaries. Requires `ollama pull`.
OLLAMA_MODEL_LIGHT = os.getenv("OLLAMA_MODEL_LIGHT", OLLAMA_MODEL)
OLLAMA_MAX_TOKENS_PER_RUN = int(os.getenv("OLLAMA_MAX_TOKENS_PER_RUN", "0"))
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text-v2-moe")
OLLAMA_EMBED_BASE_URL = os.getenv("OLLAMA_EMBED_BASE_URL", "http://localhost:11434")

ARXIV_FROM_DATE = os.getenv("ARXIV_FROM_DATE", "2020-01-01")
ARXIV_MAX_RESULTS = int(os.getenv("ARXIV_MAX_RESULTS", "2"))

# Pinecone Vector Database
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "auto-researcher-papers")
PINECONE_EMBED_DIMENSION = int(os.getenv("PINECONE_EMBED_DIMENSION", "768"))

BUCKETS = ["general_ai", "autonomous_agents", "ai_finance"]

ARXIV_CATEGORIES = {
    "general_ai": ["cs.AI", "cs.LG"],
    "autonomous_agents": ["cs.MA", "cs.AI"],
    "ai_finance": ["q-fin.ST", "q-fin.CP", "q-fin.GN"],
}

ARXIV_KEYWORDS = {
    "general_ai": [
        "large language models", "neural networks",
    ],
    "autonomous_agents": [
        "autonomous agents", "multi-agent systems", "agentic workflow",
    ],
    "ai_finance": [
        "machine learning", "AI", "algorithmic trading",
    ],
}

SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))
RRF_K = int(os.getenv("RRF_K", "60"))
RERANK_MARGIN = float(os.getenv("RERANK_MARGIN", "0.05"))
RERANK_WEIGHT_COSINE = float(os.getenv("RERANK_WEIGHT_COSINE", "0.6"))
RERANK_WEIGHT_BM25 = float(os.getenv("RERANK_WEIGHT_BM25", "0.4"))
DEDUP_THRESHOLD = float(os.getenv("DEDUP_THRESHOLD", "0.85"))
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))

# Scheduler
SCHEDULER_INTERVAL_SECONDS = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "300"))
SCHEDULER_LOOKBACK_DAYS = int(os.getenv("SCHEDULER_LOOKBACK_DAYS", "3"))
SCHEDULER_MAX_RESULTS = int(os.getenv("SCHEDULER_MAX_RESULTS", "50"))
REPORT_PERIODS = ["7d", "1m", "3m", "6m", "1y"]
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
REPORT_TIMEOUT = int(os.getenv("REPORT_TIMEOUT", "3600"))

for d in [DATA_DIR, PDFS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)