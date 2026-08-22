"""Data ingestion and chunking module."""

from gtm_copilot.ingestion.loader import load_documents, load_file
from gtm_copilot.ingestion.chunker import chunk_document, chunk_documents

__all__ = [
    "load_documents",
    "load_file",
    "chunk_document",
    "chunk_documents",
]
