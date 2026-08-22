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

# Retrieval Configuration
DEFAULT_EMBEDDING_MODEL = os.getenv("DEFAULT_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))
DEFAULT_COLLECTION_NAME = os.getenv("DEFAULT_COLLECTION_NAME", "gtm_knowledge_base")
