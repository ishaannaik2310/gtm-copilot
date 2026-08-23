"""Unit tests for HybridRetriever with Reciprocal Rank Fusion (RRF)."""

from pathlib import Path
import chromadb
import pytest

from gtm_copilot.models import Chunk
from gtm_copilot.retrieval.bm25_retriever import BM25Retriever
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.vector_store import VectorStore


def test_hybrid_retriever_rrf_fusion():
    client = chromadb.EphemeralClient()
    vector_store = VectorStore(collection_name="test_hybrid_fusion", client=client)
    bm25 = BM25Retriever()
    hybrid = HybridRetriever(vector_store=vector_store, bm25_retriever=bm25, rrf_k=60)

    chunks = [
        Chunk(
            id="chunk-strong-match",
            document_id="doc-1",
            text="Sales objection handling playbook for security and data privacy concerns.",
            metadata={"source_type": "playbook", "category": "objections"},
        ),
        Chunk(
            id="chunk-dense-only",
            document_id="doc-2",
            text="Confidentiality and customer data protection protocols for enterprise clients.",
            metadata={"source_type": "playbook", "category": "security"},
        ),
        Chunk(
            id="chunk-keyword-only",
            document_id="doc-3",
            text="Sales objection rebuttal guide with scripts for account executives.",
            metadata={"source_type": "playbook", "category": "sales_scripts"},
        ),
    ]

    hybrid.index(chunks)

    # Query matching exact keywords and concepts
    results = hybrid.retrieve(query="Sales objection handling security", top_k=3)
    assert len(results) > 0

    # chunk-strong-match should rank at top due to appearing in both dense and sparse results
    top_result = results[0]
    assert "rrf_score" in top_result.metadata
    assert top_result.metadata["rrf_score"] > 0
    assert top_result.id == "chunk-strong-match"


def test_hybrid_retriever_source_type_filter():
    client = chromadb.EphemeralClient()
    vector_store = VectorStore(collection_name="test_hybrid_filter", client=client)
    hybrid = HybridRetriever(vector_store=vector_store, rrf_k=60)

    chunks = [
        Chunk(
            id="chunk-playbook",
            document_id="doc-1",
            text="Cloud scaling infrastructure and Kubernetes monitoring best practices.",
            metadata={"source_type": "playbook"},
        ),
        Chunk(
            id="chunk-account",
            document_id="doc-2",
            text="Cloud scaling infrastructure company profile for CloudScale Inc.",
            metadata={"source_type": "account_data"},
        ),
    ]

    hybrid.index(chunks)

    results = hybrid.retrieve(
        query="Cloud scaling infrastructure",
        top_k=5,
        filter_source_type="account_data",
    )
    assert len(results) == 1
    assert results[0].id == "chunk-account"
    assert results[0].metadata["source_type"] == "account_data"


def test_hybrid_retriever_empty_query():
    client = chromadb.EphemeralClient()
    vector_store = VectorStore(collection_name="test_hybrid_empty", client=client)
    hybrid = HybridRetriever(vector_store=vector_store)

    assert hybrid.retrieve("") == []
    assert hybrid.retrieve("   ") == []
