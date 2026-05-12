import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PDFS_DIR = DATA_DIR / "pdfs"
REPORTS_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "auto_researcher.db"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text-v2-moe")

ARXIV_FROM_DATE = os.getenv("ARXIV_FROM_DATE", "2020-01-01")
ARXIV_MAX_RESULTS = int(os.getenv("ARXIV_MAX_RESULTS", "2"))

# Qdrant Vector Database
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "papers")
QDRANT_EMBED_DIMENSION = int(os.getenv("QDRANT_EMBED_DIMENSION", "768"))

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
DEDUP_THRESHOLD = float(os.getenv("DEDUP_THRESHOLD", "0.85"))
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
REPORT_PERIODS = ["7d", "6m", "1y"]

for d in [DATA_DIR, PDFS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)