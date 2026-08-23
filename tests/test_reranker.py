"""Unit tests for Cross-Encoder Reranker."""

from unittest.mock import MagicMock
import numpy as np
import pytest

from gtm_copilot.models import Chunk
from gtm_copilot.retrieval.reranker import Reranker


class MockCrossEncoder:
    """Mock CrossEncoder that returns deterministic scores for testing."""

    def __init__(self, score_mapping=None):
        self.score_mapping = score_mapping or {}

    def predict(self, pairs):
        scores = []
        for query, text in pairs:
            # Look up score or default based on text
            matched_score = 0.0
            for key, score in self.score_mapping.items():
                if key in text:
                    matched_score = score
                    break
            scores.append(matched_score)
        return np.array(scores)


def test_reranker_reordering():
    # Chunk A has superficial keyword matches but lower relevance score
    # Chunk B has high semantic relevance score
    chunk_a = Chunk(
        id="chunk-keyword-match",
        document_id="doc-1",
        text="A brief mention of pricing and licensing terms.",
        metadata={"source_type": "playbook"},
    )
    chunk_b = Chunk(
        id="chunk-semantic-match",
        document_id="doc-2",
        text="Comprehensive Ideal Customer Profile ICP definition and criteria for B2B enterprise SaaS.",
        metadata={"source_type": "playbook"},
    )

    mock_model = MockCrossEncoder(
        score_mapping={
            "Ideal Customer Profile": 8.95,
            "pricing and licensing": 1.20,
        }
    )

    reranker = Reranker(model=mock_model)
    results = reranker.rerank(
        query="What is the ideal customer profile?",
        chunks=[chunk_a, chunk_b],
        top_k=2,
    )

    assert len(results) == 2
    # chunk-semantic-match should now be first
    assert results[0].id == "chunk-semantic-match"
    assert results[0].metadata["rerank_score"] == pytest.approx(8.95)
    assert results[1].id == "chunk-keyword-match"
    assert results[1].metadata["rerank_score"] == pytest.approx(1.20)


def test_reranker_top_k_truncation():
    chunks = [
        Chunk(
            id=f"chunk-{i}",
            document_id="doc-1",
            text=f"Text content number {i}",
            metadata={},
        )
        for i in range(10)
    ]

    mock_model = MockCrossEncoder()
    mock_model.predict = MagicMock(return_value=np.linspace(0.1, 1.0, 10))

    reranker = Reranker(model=mock_model)
    results = reranker.rerank(query="test query", chunks=chunks, top_k=3)

    assert len(results) == 3
    # First result should have the highest score (1.0)
    assert results[0].metadata["rerank_score"] == pytest.approx(1.0)


def test_reranker_empty_handling():
    reranker = Reranker(model=MockCrossEncoder())
    assert reranker.rerank("query", []) == []

    chunk = Chunk(id="c1", document_id="d1", text="some text", metadata={})
    # Empty query returns original chunks up to top_k
    assert len(reranker.rerank("", [chunk])) == 1
    assert len(reranker.rerank("   ", [chunk])) == 1
