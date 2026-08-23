"""BM25 sparse keyword retriever using rank-bm25."""

import logging
import re
from typing import List, Optional

from rank_bm25 import BM25Okapi

from gtm_copilot.config import DEFAULT_INITIAL_TOP_K
from gtm_copilot.models import Chunk

logger = logging.getLogger(__name__)


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric tokens."""
    return re.findall(r"\w+", text.lower())


class BM25Retriever:
    """Sparse keyword retriever based on the BM25Okapi algorithm."""

    def __init__(
        self,
        chunks: Optional[List[Chunk]] = None,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        """Initialize the BM25Retriever.

        Args:
            chunks: Optional initial list of Chunk objects to index.
            k1: BM25 k1 parameter (term frequency saturation).
            b: BM25 b parameter (document length normalization).
        """
        self.k1 = k1
        self.b = b
        self.chunks: List[Chunk] = []
        self.bm25: Optional[BM25Okapi] = None

        if chunks:
            self.index(chunks)

    def index(self, chunks: List[Chunk]) -> None:
        """Build the BM25 index over a list of chunks.

        Args:
            chunks: List of Chunk objects to index.
        """
        if not chunks:
            self.chunks = []
            self.bm25 = None
            return

        self.chunks = list(chunks)
        tokenized_corpus = [tokenize(chunk.text) for chunk in self.chunks]
        self.bm25 = BM25Okapi(tokenized_corpus, k1=self.k1, b=self.b)
        logger.info("Indexed %d chunks in BM25Retriever", len(self.chunks))

    def query(
        self,
        text: str,
        top_k: int = DEFAULT_INITIAL_TOP_K,
        filter_source_type: Optional[str] = None,
    ) -> List[Chunk]:
        """Retrieve top-k chunks matching the query string using BM25 scoring.

        Args:
            text: Query keyword string.
            top_k: Maximum number of chunks to return.
            filter_source_type: Optional source_type filter ('playbook', 'account_data', etc.).

        Returns:
            List of matching Chunk objects sorted by BM25 relevance score descending.
        """
        if not text.strip() or self.bm25 is None or not self.chunks:
            return []

        tokenized_query = tokenize(text)
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)

        query_tokens_set = set(tokenized_query)
        scored_candidates = []
        for idx, score in enumerate(scores):
            chunk = self.chunks[idx]
            if filter_source_type is not None:
                if chunk.metadata.get("source_type") != filter_source_type:
                    continue

            chunk_tokens = tokenize(chunk.text)
            if any(t in query_tokens_set for t in chunk_tokens):
                scored_candidates.append((score, chunk))

        # Sort descending by BM25 score
        scored_candidates.sort(key=lambda item: item[0], reverse=True)

        results: List[Chunk] = []
        for score, chunk in scored_candidates[:top_k]:
            # Create a shallow copy with bm25_score populated in metadata
            chunk_copy = Chunk(
                id=chunk.id,
                document_id=chunk.document_id,
                text=chunk.text,
                embedding=chunk.embedding,
                metadata={**chunk.metadata, "bm25_score": float(score)},
            )
            results.append(chunk_copy)

        return results

    def count(self) -> int:
        """Return total number of indexed chunks."""
        return len(self.chunks)
