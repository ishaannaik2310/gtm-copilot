"""ChromaDB-backed vector store abstraction for indexing and retrieving chunks."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from gtm_copilot.config import (
    CHROMA_PERSIST_DIR,
    DEFAULT_COLLECTION_NAME,
    DEFAULT_TOP_K,
)
from gtm_copilot.models import Chunk

logger = logging.getLogger(__name__)


def sanitize_metadata_for_chroma(metadata: Dict[str, Any]) -> Dict[str, Union[str, int, float, bool]]:
    """Sanitize metadata values to ChromaDB supported scalar types (str, int, float, bool)."""
    sanitized: Dict[str, Union[str, int, float, bool]] = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif value is None:
            continue
        elif isinstance(value, (dict, list)):
            sanitized[key] = json.dumps(value)
        else:
            sanitized[key] = str(value)
    return sanitized


class VectorStore:
    """Persistent ChromaDB vector store wrapper for GTM Copilot chunks."""

    def __init__(
        self,
        persist_directory: Optional[Union[str, Path]] = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        client: Optional[ClientAPI] = None,
        embedding_function: Optional[Any] = None,
    ):
        """Initialize the ChromaDB persistent client and collection.

        Args:
            persist_directory: Local directory for Chroma storage. Defaults to config.CHROMA_PERSIST_DIR.
            collection_name: Name of the Chroma collection.
            client: Optional pre-configured Chroma client (useful for in-memory testing).
            embedding_function: Optional custom embedding function.
        """
        self.collection_name = collection_name
        self.embedding_function = embedding_function

        if client is not None:
            self.client = client
        else:
            persist_path = Path(persist_directory or CHROMA_PERSIST_DIR).resolve()
            persist_path.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(persist_path))

        get_or_create_kwargs: Dict[str, Any] = {"name": self.collection_name}
        if self.embedding_function is not None:
            get_or_create_kwargs["embedding_function"] = self.embedding_function

        self.collection: Collection = self.client.get_or_create_collection(
            **get_or_create_kwargs
        )

    def add_chunks(self, chunks: List[Chunk]) -> int:
        """Embed and upsert a batch of Chunk models into ChromaDB.

        Args:
            chunks: List of Chunk objects to store.

        Returns:
            Number of chunks successfully added.
        """
        if not chunks:
            return 0

        ids: List[str] = [chunk.id for chunk in chunks]
        documents: List[str] = [chunk.text for chunk in chunks]
        metadatas: List[Dict[str, Union[str, int, float, bool]]] = [
            sanitize_metadata_for_chroma(chunk.metadata) for chunk in chunks
        ]

        # Check if pre-computed embeddings are provided for all chunks
        has_embeddings = all(chunk.embedding is not None for chunk in chunks)
        embeddings = [chunk.embedding for chunk in chunks] if has_embeddings else None

        upsert_kwargs: Dict[str, Any] = {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
        }
        if embeddings is not None:
            upsert_kwargs["embeddings"] = embeddings

        self.collection.upsert(**upsert_kwargs)
        logger.info("Upserted %d chunks into collection '%s'", len(chunks), self.collection_name)
        return len(chunks)

    def query(
        self,
        text: str,
        top_k: int = DEFAULT_TOP_K,
        filter_source_type: Optional[str] = None,
    ) -> List[Chunk]:
        """Query top-k most relevant chunks using semantic search.

        Args:
            text: Query string.
            top_k: Number of relevant chunks to retrieve.
            filter_source_type: Optional filter by source_type (e.g. 'playbook', 'account_data').

        Returns:
            List of retrieved Chunk objects ordered by relevance.
        """
        if not text.strip():
            return []

        count = self.collection.count()
        if count == 0:
            return []

        n_results = min(top_k, count)
        where_filter: Optional[Dict[str, Any]] = None
        if filter_source_type:
            where_filter = {"source_type": filter_source_type}

        query_kwargs: Dict[str, Any] = {
            "query_texts": [text],
            "n_results": n_results,
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        results = self.collection.query(**query_kwargs)

        retrieved_chunks: List[Chunk] = []
        ids_list = results.get("ids", [[]])[0]
        docs_list = results.get("documents", [[]])[0]
        meta_list = results.get("metadatas", [[]])[0]

        for i in range(len(ids_list)):
            chunk_id = ids_list[i]
            chunk_text = docs_list[i] if i < len(docs_list) else ""
            raw_meta = meta_list[i] if i < len(meta_list) else {}
            metadata = dict(raw_meta) if raw_meta else {}
            doc_id = str(metadata.get("document_id", ""))

            chunk = Chunk(
                id=chunk_id,
                document_id=doc_id,
                text=chunk_text,
                embedding=None,
                metadata=metadata,
            )
            retrieved_chunks.append(chunk)

        return retrieved_chunks

    def count(self) -> int:
        """Return total number of items indexed in the collection."""
        return self.collection.count()

    def reset(self) -> None:
        """Delete all items in the current collection."""
        self.client.delete_collection(name=self.collection_name)
        get_or_create_kwargs: Dict[str, Any] = {"name": self.collection_name}
        if self.embedding_function is not None:
            get_or_create_kwargs["embedding_function"] = self.embedding_function
        self.collection = self.client.get_or_create_collection(**get_or_create_kwargs)
