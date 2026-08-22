"""Unit tests for document chunker engine."""

import pytest
from gtm_copilot.ingestion.chunker import (
    chunk_document,
    chunk_documents,
    split_text_into_chunks,
)
from gtm_copilot.models import Chunk, Document


def test_split_text_into_chunks_small():
    text = "Short text with seven distinct words in it."
    chunks = split_text_into_chunks(text, chunk_size=20, chunk_overlap=5)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_split_text_into_chunks_empty():
    assert split_text_into_chunks("") == []
    assert split_text_into_chunks("   \n\t  ") == []


def test_split_text_into_chunks_overlap():
    words = [f"word_{i}" for i in range(100)]
    text = " ".join(words)
    chunk_size = 30
    chunk_overlap = 10
    step = chunk_size - chunk_overlap  # 20 words per step

    chunks = split_text_into_chunks(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    assert len(chunks) == 5  # 0-30, 20-50, 40-70, 60-90, 80-100

    # Verify overlap between chunk 0 and chunk 1
    chunk_0_words = chunks[0].split()
    chunk_1_words = chunks[1].split()
    assert chunk_0_words[-10:] == chunk_1_words[:10]


def test_split_text_invalid_overlap():
    with pytest.raises(ValueError, match="chunk_overlap.*must be strictly less"):
        split_text_into_chunks("test text", chunk_size=10, chunk_overlap=10)


def test_split_text_invalid_chunk_size():
    with pytest.raises(ValueError, match="chunk_size must be strictly positive"):
        split_text_into_chunks("test text", chunk_size=0, chunk_overlap=0)


def test_split_text_negative_overlap():
    with pytest.raises(ValueError, match="chunk_overlap must be non-negative"):
        split_text_into_chunks("test text", chunk_size=10, chunk_overlap=-1)


def test_chunk_document_metadata_preservation():
    doc = Document(
        source_type="playbook",
        content="This is a test playbook content for chunking verification. " * 30,
        metadata={"author": "RevOps", "version": "1.0"},
    )

    chunks = chunk_document(doc, chunk_size=50, chunk_overlap=10)
    assert len(chunks) > 1

    for idx, chunk in enumerate(chunks):
        assert isinstance(chunk, Chunk)
        assert chunk.document_id == doc.id
        assert chunk.embedding is None
        assert chunk.metadata["source_type"] == "playbook"
        assert chunk.metadata["author"] == "RevOps"
        assert chunk.metadata["version"] == "1.0"
        assert chunk.metadata["chunk_index"] == idx
        assert chunk.metadata["total_chunks"] == len(chunks)
        assert chunk.metadata["word_count"] > 0


def test_chunk_documents_batch():
    doc1 = Document(
        source_type="playbook",
        content="Document 1 content words.",
    )
    doc2 = Document(
        source_type="account_data",
        content="Document 2 content words.",
    )

    all_chunks = chunk_documents([doc1, doc2], chunk_size=50, chunk_overlap=10)
    assert len(all_chunks) == 2
    assert all_chunks[0].document_id == doc1.id
    assert all_chunks[0].metadata["source_type"] == "playbook"
    assert all_chunks[1].document_id == doc2.id
    assert all_chunks[1].metadata["source_type"] == "account_data"
