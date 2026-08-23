"""Hybrid retriever combining dense vector search and sparse BM25 search with Reciprocal Rank Fusion (RRF)."""

import logging
from typing import Dict, List, Optional

from gtm_copilot.config import DEFAULT_INITIAL_TOP_K, DEFAULT_RRF_K
from gtm_copilot.models import Chunk
from gtm_copilot.retrieval.bm25_retriever import BM25Retriever
from gtm_copilot.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid search retriever merging dense vector retrieval and sparse BM25 with RRF."""

    def __init__(
        self,
        vector_store: VectorStore,
        bm25_retriever: Optional[BM25Retriever] = None,
        rrf_k: int = DEFAULT_RRF_K,
    ):
        """Initialize HybridRetriever.

        Args:
            vector_store: Initialized VectorStore instance (dense search).
            bm25_retriever: Optional BM25Retriever instance (sparse search). If not provided, a new one is created.
            rrf_k: Smoothing constant for Reciprocal Rank Fusion formula (default: 60).
        """
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever or BM25Retriever()
        self.rrf_k = rrf_k

    def index(self, chunks: List[Chunk]) -> None:
        """Index a batch of chunks in both the vector store and BM25 index.

        Args:
            chunks: List of Chunk objects to index.
        """
        if not chunks:
            return
        self.vector_store.add_chunks(chunks)
        self.bm25_retriever.index(chunks)
        logger.info("Hybrid indexed %d chunks across vector store and BM25", len(chunks))

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_INITIAL_TOP_K,
        filter_source_type: Optional[str] = None,
    ) -> List[Chunk]:
        """Execute hybrid search using Reciprocal Rank Fusion (RRF).

        Args:
            query: Search query text.
            top_k: Maximum number of merged results to return.
            filter_source_type: Optional filter for source_type ('playbook', 'account_data', etc.).

        Returns:
            List of top-k fused Chunk objects sorted by RRF score descending.
        """
        if not query.strip():
            return []

        # Retrieve a broader pool from each individual retriever before fusing
        pool_size = max(top_k * 2, 20)

        dense_chunks = self.vector_store.query(
            text=query,
            top_k=pool_size,
            filter_source_type=filter_source_type,
        )
        sparse_chunks = self.bm25_retriever.query(
            text=query,
            top_k=pool_size,
            filter_source_type=filter_source_type,
        )

        # Map to store aggregated RRF scores and chunk objects
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Chunk] = {}
        dense_ranks: Dict[str, int] = {}
        sparse_ranks: Dict[str, int] = {}

        # 1. Process Dense Results (1-based ranking)
        for rank, chunk in enumerate(dense_chunks, start=1):
            chunk_id = chunk.id
            chunk_map[chunk_id] = chunk
            dense_ranks[chunk_id] = rank
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (self.rrf_k + rank))

        # 2. Process Sparse Results (1-based ranking)
        for rank, chunk in enumerate(sparse_chunks, start=1):
            chunk_id = chunk.id
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = chunk
            sparse_ranks[chunk_id] = rank
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (self.rrf_k + rank))

        # 3. Sort all candidate chunks by RRF score descending
        sorted_chunk_ids = sorted(
            rrf_scores.keys(),
            key=lambda cid: rrf_scores[cid],
            reverse=True,
        )

        fused_results: List[Chunk] = []
        for cid in sorted_chunk_ids[:top_k]:
            original_chunk = chunk_map[cid]
            fused_metadata = dict(original_chunk.metadata)
            fused_metadata.update(
                {
                    "rrf_score": rrf_scores[cid],
                    "dense_rank": dense_ranks.get(cid),
                    "sparse_rank": sparse_ranks.get(cid),
                }
            )

            fused_chunk = Chunk(
                id=original_chunk.id,
                document_id=original_chunk.document_id,
                text=original_chunk.text,
                embedding=original_chunk.embedding,
                metadata=fused_metadata,
            )
            fused_results.append(fused_chunk)

        return fused_results
