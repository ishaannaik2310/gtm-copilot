"""Integration test for the full end-to-end RAG retrieval pipeline:
load docs -> chunk -> hybrid index (Vector + BM25) -> hybrid retrieve -> rerank.
"""

from pathlib import Path
import chromadb
import pytest

from gtm_copilot.ingestion.chunker import chunk_documents
from gtm_copilot.ingestion.loader import load_documents
from gtm_copilot.retrieval.bm25_retriever import BM25Retriever
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.reranker import Reranker
from gtm_copilot.retrieval.vector_store import VectorStore


def test_full_retrieval_pipeline_integration(capsys):
    # 1. Load sample playbook and account docs
    documents = load_documents()
    assert len(documents) >= 2, "Expected sample playbook and account data to be loaded"

    # 2. Chunk documents
    chunks = chunk_documents(documents, chunk_size=300, chunk_overlap=40)
    assert len(chunks) >= 2, "Expected chunks to be generated"

    # 3. Setup Hybrid Index (ChromaDB + BM25)
    chroma_client = chromadb.EphemeralClient()
    vector_store = VectorStore(
        collection_name="test_pipeline_collection",
        client=chroma_client,
    )
    bm25_retriever = BM25Retriever()
    hybrid_retriever = HybridRetriever(
        vector_store=vector_store,
        bm25_retriever=bm25_retriever,
        rrf_k=60,
    )
    hybrid_retriever.index(chunks)

    # 4. Hybrid Retrieve
    query = "what is the ICP for our sales playbook"
    retrieved_candidates = hybrid_retriever.retrieve(
        query=query,
        top_k=5,
        filter_source_type="playbook",
    )
    assert len(retrieved_candidates) > 0, "Expected hybrid retrieval to return matching chunks"
    assert all(c.metadata.get("source_type") == "playbook" for c in retrieved_candidates)

    # 5. Cross-Encoder Rerank
    # Mock or real scoring model
    class MockPipelineCrossEncoder:
        def predict(self, pairs):
            scores = []
            for q, text in pairs:
                score = 0.0
                if "Ideal Customer Profile" in text or "ICP" in text:
                    score += 5.0
                if "Series B" in text:
                    score += 2.0
                scores.append(score)
            return scores

    reranker = Reranker(model=MockPipelineCrossEncoder())
    reranked_chunks = reranker.rerank(
        query=query,
        chunks=retrieved_candidates,
        top_k=3,
    )

    assert len(reranked_chunks) > 0
    top_chunk = reranked_chunks[0]

    # Print top result for verification
    print(f"\n--- TOP RETRIEVED & RERANKED RESULT ---")
    print(f"ID: {top_chunk.id}")
    print(f"RRF Score: {top_chunk.metadata.get('rrf_score')}")
    print(f"Rerank Score: {top_chunk.metadata.get('rerank_score')}")
    print(f"Text Snippet: {top_chunk.text[:200]}...")

    # Assert top chunk is grounded in ICP content
    assert "ICP" in top_chunk.text or "Ideal Customer Profile" in top_chunk.text
