"""Unit tests for BM25 sparse keyword retriever."""

import pytest
from gtm_copilot.models import Chunk
from gtm_copilot.retrieval.bm25_retriever import BM25Retriever, tokenize


def test_tokenize():
    text = "B2B SaaS Sales Playbook (ICP criteria & messaging)!"
    tokens = tokenize(text)
    assert "b2b" in tokens
    assert "saas" in tokens
    assert "playbook" in tokens
    assert "icp" in tokens


def test_bm25_retriever_query():
    chunks = [
        Chunk(
            id="chunk-icp",
            document_id="doc-1",
            text="Ideal Customer Profile ICP criteria: Series B SaaS companies with 100 to 1000 employees.",
            metadata={"source_type": "playbook", "topic": "icp"},
        ),
        Chunk(
            id="chunk-objection",
            document_id="doc-1",
            text="Objection handling: Dealing with proprietary data privacy and security concerns.",
            metadata={"source_type": "playbook", "topic": "objection"},
        ),
        Chunk(
            id="chunk-account",
            document_id="doc-2",
            text="CloudScale Data Inc is a Series B cloud infrastructure startup.",
            metadata={"source_type": "account_data", "topic": "profile"},
        ),
    ]

    retriever = BM25Retriever(chunks=chunks)
    assert retriever.count() == 3

    # Query for objection handling
    results = retriever.query("objection handling security", top_k=2)
    assert len(results) >= 1
    assert results[0].id == "chunk-objection"
    assert "bm25_score" in results[0].metadata
    assert results[0].metadata["bm25_score"] > 0


def test_bm25_retriever_source_type_filter():
    chunks = [
        Chunk(
            id="chunk-1",
            document_id="doc-1",
            text="Series B cloud infrastructure growth metrics in playbook.",
            metadata={"source_type": "playbook"},
        ),
        Chunk(
            id="chunk-2",
            document_id="doc-2",
            text="Series B cloud infrastructure account profile data.",
            metadata={"source_type": "account_data"},
        ),
    ]

    retriever = BM25Retriever(chunks=chunks)

    # Query with filter_source_type="account_data"
    results = retriever.query(
        "Series B cloud infrastructure",
        top_k=5,
        filter_source_type="account_data",
    )
    assert len(results) == 1
    assert results[0].id == "chunk-2"
    assert results[0].metadata["source_type"] == "account_data"


def test_bm25_retriever_empty_handling():
    retriever = BM25Retriever()
    assert retriever.query("test query") == []

    chunks = [
        Chunk(
            id="chunk-1",
            document_id="doc-1",
            text="Sample text",
            metadata={"source_type": "playbook"},
        )
    ]
    retriever.index(chunks)
    assert retriever.query("") == []
    assert retriever.query("   ") == []
