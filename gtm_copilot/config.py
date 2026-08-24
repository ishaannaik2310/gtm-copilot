"""Configuration settings and environment variable management for GTM Ops Copilot."""

import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DATA_DIR = PROJECT_ROOT / os.getenv("DATA_DIR", "data")
PLAYBOOKS_DIR = DATA_DIR / os.getenv("PLAYBOOKS_DIR_NAME", "playbooks")
SAMPLE_ACCOUNTS_DIR = DATA_DIR / os.getenv("SAMPLE_ACCOUNTS_DIR_NAME", "sample_accounts")
CHROMA_PERSIST_DIR = PROJECT_ROOT / os.getenv("CHROMA_PERSIST_DIR", "chroma_db")

# Chunking Configuration
DEFAULT_CHUNK_SIZE = int(os.getenv("DEFAULT_CHUNK_SIZE", "400"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("DEFAULT_CHUNK_OVERLAP", "50"))

# Retrieval & Hybrid Search Configuration
DEFAULT_EMBEDDING_MODEL = os.getenv("DEFAULT_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))
DEFAULT_INITIAL_TOP_K = int(os.getenv("DEFAULT_INITIAL_TOP_K", "10"))
DEFAULT_RERANK_TOP_K = int(os.getenv("DEFAULT_RERANK_TOP_K", "5"))
DEFAULT_RRF_K = int(os.getenv("DEFAULT_RRF_K", "60"))
DEFAULT_COLLECTION_NAME = os.getenv("DEFAULT_COLLECTION_NAME", "gtm_knowledge_base")

# Reranker Configuration
DEFAULT_RERANKER_MODEL = os.getenv(
    "DEFAULT_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

# LLM Provider Configuration (Google Gemini)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_GEMINI_MODEL = os.getenv("DEFAULT_GEMINI_MODEL", "gemini-2.0-flash")

# Web Ingestion & Scraping Configuration
WEB_FETCH_TIMEOUT_SECONDS = float(os.getenv("WEB_FETCH_TIMEOUT_SECONDS", "10.0"))
MAX_WEB_CONTENT_CHARS = int(os.getenv("MAX_WEB_CONTENT_CHARS", "8000"))
