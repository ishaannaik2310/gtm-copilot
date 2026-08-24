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


class ResearchInput(BaseModel):
    """Input parameters for the Research Agent."""

    company_name: Optional[str] = Field(
        default=None,
        description="Name of the target company to research.",
    )
    url: Optional[str] = Field(
        default=None,
        description="Website or homepage URL of the target company.",
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate that at least one of company_name or url is supplied."""
        has_name = self.company_name and self.company_name.strip()
        has_url = self.url and self.url.strip()
        if not has_name and not has_url:
            raise ValueError("At least one of 'company_name' or 'url' must be provided.")


class ResearchOutput(BaseModel):
    """Structured research findings and grounded facts extracted by the Research Agent."""

    company_name: Optional[str] = Field(
        default=None,
        description="Extracted official company name.",
    )
    industry: Optional[str] = Field(
        default=None,
        description="Primary industry or business sector.",
    )
    products_or_services: List[str] = Field(
        default_factory=list,
        description="Core products, platform offerings, or services provided.",
    )
    apparent_company_size_signals: Optional[str] = Field(
        default=None,
        description="Signals regarding company size, stage, employee count, or ARR tier.",
    )
    recent_news_or_signals: List[str] = Field(
        default_factory=list,
        description="Recent announcements, product launches, partnerships, or leadership changes.",
    )
    notable_tech_or_tools_mentioned: List[str] = Field(
        default_factory=list,
        description="Technology stack signals, tools, integrations, or platforms referenced.",
    )
    source_urls: List[str] = Field(
        default_factory=list,
        description="URLs visited and used during research.",
    )
    raw_context_used: List[str] = Field(
        default_factory=list,
        description="Snippets of internal playbook or external web context utilized.",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Any non-fatal error messages encountered during web retrieval or extraction.",
    )
