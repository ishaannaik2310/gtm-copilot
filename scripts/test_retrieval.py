"""Interactive CLI smoke-test script for testing hybrid retrieval and reranking."""

import sys
from pathlib import Path
from typing import Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import chromadb
from gtm_copilot.ingestion.chunker import chunk_documents
from gtm_copilot.ingestion.loader import load_documents
from gtm_copilot.retrieval.bm25_retriever import BM25Retriever
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.reranker import Reranker
from gtm_copilot.retrieval.vector_store import VectorStore


def setup_pipeline():
    """Load documents, chunk them, and index into VectorStore and BM25."""
    print("=" * 60)
    print("  GTM Ops Copilot - Interactive Retrieval Smoke Test")
    print("=" * 60)
    print("\n[1/3] Loading sample documents...")
    docs = load_documents()
    print(f"      Loaded {len(docs)} documents:")
    for d in docs:
        print(f"       - [{d.source_type}] {d.metadata.get('file_name', 'unknown')} ({d.metadata.get('char_count', 0)} chars)")

    print("\n[2/3] Chunking documents...")
    chunks = chunk_documents(docs, chunk_size=300, chunk_overlap=40)
    print(f"      Generated {len(chunks)} chunks.")

    print("\n[3/3] Initializing Hybrid Retriever (ChromaDB + BM25) and Reranker...")
    chroma_client = chromadb.EphemeralClient()
    vector_store = VectorStore(
        collection_name="cli_smoke_test",
        client=chroma_client,
    )
    bm25 = BM25Retriever()
    hybrid = HybridRetriever(vector_store=vector_store, bm25_retriever=bm25, rrf_k=60)
    hybrid.index(chunks)

    reranker = Reranker()
    print("      Ready!\n")
    return hybrid, reranker


def execute_search(hybrid: HybridRetriever, reranker: Reranker, query: str, top_k: int = 3, filter_source_type: Optional[str] = None):
    """Execute hybrid search and reranking on the query string."""
    print(f"\nQuery: '{query}'")
    if filter_source_type:
        print(f"Filter source_type: {filter_source_type}")

    # 1. Hybrid Retrieval (dense + sparse with RRF)
    candidates = hybrid.retrieve(
        query=query,
        top_k=10,
        filter_source_type=filter_source_type,
    )

    if not candidates:
        print("No matching chunks found.")
        return

    # 2. Cross-Encoder Reranking
    reranked = reranker.rerank(query=query, chunks=candidates, top_k=top_k)

    print(f"\n--- Top {len(reranked)} Reranked Results ---")
    for i, chunk in enumerate(reranked, start=1):
        meta = chunk.metadata
        dense_rank = meta.get("dense_rank", "N/A")
        sparse_rank = meta.get("sparse_rank", "N/A")
        rrf_score = meta.get("rrf_score", 0.0)
        rerank_score = meta.get("rerank_score", 0.0)
        source_type = meta.get("source_type", "unknown")
        file_name = meta.get("file_name", "unknown")

        print(f"\n[{i}] Chunk ID: {chunk.id[:8]}... (Document: {chunk.document_id[:8]}...)")
        print(f"    Source: {source_type} | File: {file_name}")
        print(f"    Scores: Dense Rank: {dense_rank} | Sparse Rank: {sparse_rank} | RRF Score: {rrf_score:.6f} | Rerank Score: {rerank_score:.4f}")
        print(f"    Text:")
        snippet = chunk.text.strip().replace("\n", " ")
        if len(snippet) > 280:
            snippet = snippet[:280] + "..."
        print(f"      \"{snippet}\"")


def main():
    hybrid, reranker = setup_pipeline()

    # If query was passed via command line argument, run once and exit
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        execute_search(hybrid, reranker, query=query, top_k=3)
        return

    # Otherwise enter interactive loop
    print("Enter a search query below (or type 'exit' or 'q' to quit).")
    print("Tip: You can prefix with 'playbook:' or 'account:' to filter by source.\n")

    while True:
        try:
            raw_input = input("gtm-retrieval> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if not raw_input:
            continue

        if raw_input.lower() in {"exit", "quit", "q"}:
            print("Goodbye!")
            break

        filter_source_type = None
        query = raw_input
        if raw_input.startswith("playbook:"):
            filter_source_type = "playbook"
            query = raw_input[len("playbook:") :].strip()
        elif raw_input.startswith("account:"):
            filter_source_type = "account_data"
            query = raw_input[len("account:") :].strip()

        execute_search(hybrid, reranker, query=query, top_k=3, filter_source_type=filter_source_type)
        print()


if __name__ == "__main__":
    main()
