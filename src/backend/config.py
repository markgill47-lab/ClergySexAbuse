from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Data paths
DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = DATA_DIR / "db"
DB_PATH = DB_DIR / "clergy_abuse.db"
RAW_DIR = DATA_DIR / "raw"
DOCUMENTS_DIR = DATA_DIR / "documents"
EXPORTS_DIR = DATA_DIR / "exports"

# Prior project paths (for importing existing data)
VUETEST_DIR = Path("C:/Projects/VueTest")
VUETEST_DATA = VUETEST_DIR / "src" / "data" / "clergy_all_states.json"
VUETEST_SUMMARIES = VUETEST_DIR / "src" / "data" / "state_summaries.json"

MN_PROJECT_DIR = Path("C:/Projects/MN-Clergy-Abuse")
MN_PROFILES_DIR = MN_PROJECT_DIR / "pipeline" / "data" / "profiles"
MN_PDFS_DIR = MN_PROJECT_DIR / "pipeline" / "data" / "pdfs"
MN_IMAGES_DIR = MN_PROJECT_DIR / "pipeline" / "data" / "images"
MN_TRANSCRIPTS_DIR = MN_PROJECT_DIR / "pipeline" / "data" / "transcripts"
MN_PORTRAITS_DIR = MN_PROJECT_DIR / "pipeline" / "data" / "portraits"
MN_INDEX = MN_PROFILES_DIR / "_index.json"

# Database
DATABASE_URL = f"sqlite:///{DB_PATH}"

# RAG settings
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSIONS = 384
TOP_K = 10
SIMILARITY_THRESHOLD = 0.25

# LLM settings
LLM_MODEL = "claude-sonnet-4-20250514"
MAX_CONVERSATION_TURNS = 20

# Scraping
SCRAPE_DELAY_SECONDS = 0.4  # ~2.5 req/sec
USER_AGENT = "ClergyAbuseResearch/0.1 (academic research; contact: research@example.com)"
