"""Unit tests for ChromaDB vector store wrapper."""

from pathlib import Path
import pytest
import chromadb
from gtm_copilot.models import Chunk
from gtm_copilot.retrieval.vector_store import (
    VectorStore,
    sanitize_metadata_for_chroma,
)


def test_sanitize_metadata_for_chroma():
    meta = {
        "str_val": "hello",
        "int_val": 42,
        "float_val": 3.14,
        "bool_val": True,
        "none_val": None,
        "list_val": ["a", "b"],
        "dict_val": {"nested": "value"},
    }
    sanitized = sanitize_metadata_for_chroma(meta)
    assert sanitized["str_val"] == "hello"
    assert sanitized["int_val"] == 42
    assert sanitized["float_val"] == 3.14
    assert sanitized["bool_val"] is True
    assert "none_val" not in sanitized
    assert sanitized["list_val"] == '["a", "b"]'
    assert sanitized["dict_val"] == '{"nested": "value"}'


def test_vector_store_add_and_query(tmp_path: Path):
    client = chromadb.EphemeralClient()
    store = VectorStore(
        collection_name="test_collection",
        client=client,
    )

    chunks = [
        Chunk(
            id="chunk-1",
            document_id="doc-1",
            text="Ideal customer profile consists of B2B SaaS companies with 100-1000 employees.",
            metadata={"source_type": "playbook", "topic": "icp"},
        ),
        Chunk(
            id="chunk-2",
            document_id="doc-2",
            text="Acme Corp is a Series B cloud security startup with 250 employees.",
            metadata={"source_type": "account_data", "company": "Acme"},
        ),
    ]

    added = store.add_chunks(chunks)
    assert added == 2
    assert store.count() == 2

    # Query without filter
    results = store.query(text="What is the ideal customer profile?", top_k=2)
    assert len(results) >= 1
    assert any("B2B SaaS" in c.text for c in results)

    # Query with source_type filter
    playbook_results = store.query(
        text="Series B cloud security startup",
        top_k=2,
        filter_source_type="playbook",
    )
    assert len(playbook_results) == 1
    assert playbook_results[0].metadata["source_type"] == "playbook"

    # Reset
    store.reset()
    assert store.count() == 0
