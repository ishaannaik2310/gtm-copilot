"""Document chunking engine with overlap and metadata preservation."""

import re
from typing import Any, Dict, List, Optional
from gtm_copilot.config import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE
from gtm_copilot.models import Chunk, Document


def approximate_token_count(text: str) -> int:
    """Estimate token count using whitespace and punctuation word tokens (~1.3 tokens/word approx).

    For consistent chunking without hard dependency on external tokenizers,
    word count is used as the primary unit with 1 word ~= 1-1.3 tokens.
    """
    words = re.findall(r"\S+", text)
    return len(words)


def validate_chunk_params(chunk_size: int, chunk_overlap: int) -> None:
    """Validate chunk size and overlap constraints."""
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be strictly positive (greater than 0), got {chunk_size}")
    if chunk_overlap < 0:
        raise ValueError(f"chunk_overlap must be non-negative (>= 0), got {chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size})"
        )


def split_text_into_chunks(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """Split raw text into overlapping chunks respecting paragraph or sentence boundaries.

    Args:
        text: Input text string.
        chunk_size: Target maximum words per chunk (~300-500 words/tokens).
        chunk_overlap: Overlap in words between consecutive chunks.

    Returns:
        List of text chunk strings.
    """
    validate_chunk_params(chunk_size, chunk_overlap)

    cleaned = text.strip()
    if not cleaned:
        return []

    words = cleaned.split()
    total_words = len(words)

    if total_words <= chunk_size:
        return [cleaned]

    chunks: List[str] = []
    step = chunk_size - chunk_overlap
    start = 0

    while start < total_words:
        end = min(start + chunk_size, total_words)
        chunk_words = words[start:end]
        chunk_str = " ".join(chunk_words)
        chunks.append(chunk_str)

        if end >= total_words:
            break
        start += step

    return chunks


def chunk_document(
    doc: Document,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Chunk]:
    """Convert a single Document into a list of Chunk models with preserved metadata.

    Args:
        doc: The source Document.
        chunk_size: Maximum words/tokens per chunk.
        chunk_overlap: Overlap words/tokens between chunks.

    Returns:
        List of Chunk objects with metadata propagated from the parent Document.
    """
    text_chunks = split_text_into_chunks(
        text=doc.content,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    total_chunks = len(text_chunks)
    chunks: List[Chunk] = []

    for idx, chunk_text in enumerate(text_chunks):
        chunk_meta: Dict[str, Any] = dict(doc.metadata)
        chunk_meta.update(
            {
                "source_type": doc.source_type,
                "document_id": doc.id,
                "chunk_index": idx,
                "total_chunks": total_chunks,
                "word_count": len(chunk_text.split()),
                "char_count": len(chunk_text),
            }
        )

        chunk = Chunk(
            document_id=doc.id,
            text=chunk_text,
            embedding=None,
            metadata=chunk_meta,
        )
        chunks.append(chunk)

    return chunks


def chunk_documents(
    docs: List[Document],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Chunk]:
    """Chunk a batch of Document objects into a flat list of Chunks.

    Args:
        docs: List of Document objects to chunk.
        chunk_size: Maximum words/tokens per chunk.
        chunk_overlap: Overlap words/tokens between chunks.

    Returns:
        Flat list of all generated Chunk objects.
    """
    all_chunks: List[Chunk] = []
    for doc in docs:
        all_chunks.extend(
            chunk_document(
                doc=doc,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )
    return all_chunks
