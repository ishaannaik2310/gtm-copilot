"""Cross-Encoder reranker module for post-retrieval relevance scoring."""

import logging
from typing import Any, List, Optional

from gtm_copilot.config import DEFAULT_RERANK_TOP_K, DEFAULT_RERANKER_MODEL
from gtm_copilot.models import Chunk

logger = logging.getLogger(__name__)


class Reranker:
    """Re-ranks candidate chunks using a cross-encoder transformer model."""

    def __init__(
        self,
        model_name: str = DEFAULT_RERANKER_MODEL,
        model: Optional[Any] = None,
    ):
        """Initialize the Reranker.

        Args:
            model_name: HuggingFace model identifier for the CrossEncoder.
            model: Optional pre-initialized model instance (useful for testing and dependency injection).
        """
        self.model_name = model_name
        self._model = model

    def _get_model(self) -> Any:
        """Lazy-load the CrossEncoder model when needed."""
        if self._model is None:
            logger.info("Loading CrossEncoder model '%s'...", self.model_name)
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int = DEFAULT_RERANK_TOP_K,
    ) -> List[Chunk]:
        """Rerank a list of candidate chunks based on cross-encoder similarity with query.

        Args:
            query: User or agent search query.
            chunks: Candidate Chunk objects returned by initial retrieval.
            top_k: Number of highest-scoring chunks to return.

        Returns:
            List of top-k Chunk objects sorted by cross-encoder score descending.
        """
        if not chunks:
            return []

        if not query.strip():
            return chunks[:top_k]

        model = self._get_model()
        pairs = [[query, chunk.text] for chunk in chunks]

        # Compute cross-encoder relevance logits
        raw_scores = model.predict(pairs)

        # Handle single chunk score output format
        if hasattr(raw_scores, "tolist"):
            scores = raw_scores.tolist()
        elif isinstance(raw_scores, (int, float)):
            scores = [float(raw_scores)]
        else:
            scores = list(raw_scores)

        scored_chunks = []
        for score, chunk in zip(scores, chunks):
            scored_chunks.append((float(score), chunk))

        # Sort descending by cross-encoder score
        scored_chunks.sort(key=lambda item: item[0], reverse=True)

        reranked_results: List[Chunk] = []
        for score, chunk in scored_chunks[:top_k]:
            meta = dict(chunk.metadata)
            meta["rerank_score"] = float(score)

            reranked_chunk = Chunk(
                id=chunk.id,
                document_id=chunk.document_id,
                text=chunk.text,
                embedding=chunk.embedding,
                metadata=meta,
            )
            reranked_results.append(reranked_chunk)

        return reranked_results
