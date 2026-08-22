"""Pydantic v2 domain models for GTM Ops Copilot."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class Document(BaseModel):
    """Raw document ingested from file, web, or account data source."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: Literal["playbook", "account_data", "web"] = Field(
        ...,
        description="Category of the source document: playbook, account_data, or web.",
    )
    content: str = Field(..., description="Full text content of the document.")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata such as file name, path, author, tags.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the document was created or ingested.",
    )


class Chunk(BaseModel):
    """Text chunk derived from a Document with embedding and metadata."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = Field(..., description="ID of the parent Document.")
    text: str = Field(..., description="Chunk text content.")
    embedding: Optional[List[float]] = Field(
        default=None,
        description="Vector embedding of the chunk text.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Chunk-level metadata including source_type and chunk index.",
    )


class Account(BaseModel):
    """Target account data model representing a company profile."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str = Field(..., description="Name of the company.")
    domain: str = Field(..., description="Primary domain or website URL.")
    industry: Optional[str] = Field(
        default=None,
        description="Primary industry classification.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structured account data (e.g. employee count, tech stack).",
    )
