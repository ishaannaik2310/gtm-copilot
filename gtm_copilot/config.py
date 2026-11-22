"""Configuration settings and environment variable management for GTM Ops Copilot."""

import logging
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Base Paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)
DATA_DIR = PROJECT_ROOT / (os.getenv("DATA_DIR") or "data")
PLAYBOOKS_DIR = DATA_DIR / (os.getenv("PLAYBOOKS_DIR_NAME") or "playbooks")
SAMPLE_ACCOUNTS_DIR = DATA_DIR / (os.getenv("SAMPLE_ACCOUNTS_DIR_NAME") or "sample_accounts")
CHROMA_PERSIST_DIR = PROJECT_ROOT / (os.getenv("CHROMA_PERSIST_DIR") or "chroma_db")

# Chunking Configuration
DEFAULT_CHUNK_SIZE = int(os.getenv("DEFAULT_CHUNK_SIZE") or "400")
DEFAULT_CHUNK_OVERLAP = int(os.getenv("DEFAULT_CHUNK_OVERLAP") or "50")

# Retrieval & Hybrid Search Configuration
DEFAULT_EMBEDDING_MODEL = os.getenv("DEFAULT_EMBEDDING_MODEL") or "all-MiniLM-L6-v2"
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K") or "5")
DEFAULT_INITIAL_TOP_K = int(os.getenv("DEFAULT_INITIAL_TOP_K") or "10")
DEFAULT_RERANK_TOP_K = int(os.getenv("DEFAULT_RERANK_TOP_K") or "5")
DEFAULT_RRF_K = int(os.getenv("DEFAULT_RRF_K") or "60")
DEFAULT_COLLECTION_NAME = os.getenv("DEFAULT_COLLECTION_NAME") or "gtm_knowledge_base"

# Reranker Configuration
DEFAULT_RERANKER_MODEL = (
    os.getenv("DEFAULT_RERANKER_MODEL") or "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


def sanitize_api_key(val: Optional[str]) -> str:
    """Sanitize API key by stripping whitespace, trailing newlines,

    surrounding quotes (' or "), and leading 'GEMINI_API_KEY=' prefix.
    """
    if not val:
        return ""
    cleaned = val.strip()
    # Strip a single pair of surrounding quotes if present
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        if len(cleaned) >= 2:
            cleaned = cleaned[1:-1].strip()
    # Strip leading "GEMINI_API_KEY=" prefix if pasted by mistake
    if cleaned.startswith("GEMINI_API_KEY="):
        cleaned = cleaned[len("GEMINI_API_KEY=") :].strip()
    # Strip surrounding quotes again in case it was GEMINI_API_KEY="key" or GEMINI_API_KEY='key'
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        if len(cleaned) >= 2:
            cleaned = cleaned[1:-1].strip()
    return cleaned


def log_gemini_key_status(key: Optional[str] = None) -> None:
    """Log non-sensitive diagnostic info about GEMINI_API_KEY without exposing the key itself.

    Logs whether the key is set, its length, and whether it starts with 'AIza'.
    Warns clearly if it's empty or doesn't start with 'AIza'.
    """
    resolved = key if key is not None else GEMINI_API_KEY
    is_set = bool(resolved)
    length = len(resolved) if resolved else 0
    starts_with_aiza = resolved.startswith("AIza") if resolved else False

    if not is_set:
        logger.warning(
            "GEMINI_API_KEY check on startup: NOT SET (length=0, starts_with_AIza=False). "
            "Gemini API calls will fail. Please set GEMINI_API_KEY on the server."
        )
    elif not starts_with_aiza:
        logger.warning(
            "GEMINI_API_KEY check on startup: SET but UNEXPECTED FORMAT (length=%d, starts_with_AIza=False). "
            "Google Gemini API keys typically begin with 'AIza'. Please verify GEMINI_API_KEY on the server.",
            length,
        )
    else:
        logger.info(
            "GEMINI_API_KEY check on startup: SET (length=%d, starts_with_AIza=True).",
            length,
        )


# LLM Provider Configuration (Google Gemini)
GEMINI_API_KEY = sanitize_api_key(os.getenv("GEMINI_API_KEY"))
DEFAULT_GEMINI_MODEL = (os.getenv("DEFAULT_GEMINI_MODEL") or "gemini-flash-lite-latest").strip().strip("'\"")

log_gemini_key_status(GEMINI_API_KEY)

# Web Ingestion & Scraping Configuration
WEB_FETCH_TIMEOUT_SECONDS = float(os.getenv("WEB_FETCH_TIMEOUT_SECONDS") or "10.0")
MAX_WEB_CONTENT_CHARS = int(os.getenv("MAX_WEB_CONTENT_CHARS") or "8000")
