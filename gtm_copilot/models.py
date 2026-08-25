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


class ICPClassification(BaseModel):
    """Evaluation of how well a target company aligns with internal ICP criteria."""

    fit_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fit score between 0.0 (poor) and 1.0 (perfect), or None if unknown/failed.",
    )
    fit_label: Literal["strong_fit", "possible_fit", "poor_fit", "unknown"] = Field(
        ...,
        description="Discrete classification label based on playbook criteria.",
    )
    rationale: str = Field(
        ...,
        description="Detailed explanation of the ICP fit evaluation and evidence mapping.",
    )
    matched_criteria: List[str] = Field(
        default_factory=list,
        description="List of specific ICP criteria explicitly satisfied by company signals.",
    )
    mismatched_criteria: List[str] = Field(
        default_factory=list,
        description="List of specific ICP criteria that company signals fail or contradict.",
    )


class AccountBrief(BaseModel):
    """Actionable account intelligence brief synthesized for sales and GTM teams."""

    company_name: str = Field(..., description="Target company name.")
    industry: Optional[str] = Field(default=None, description="Primary industry sector.")
    icp_classification: ICPClassification = Field(
        ...,
        description="ICP fit classification and criteria breakdown.",
    )
    executive_summary: str = Field(
        ...,
        description="High-level narrative summary of company business and fit.",
    )
    key_products_or_services: List[str] = Field(
        default_factory=list,
        description="Core products and offerings identified.",
    )
    likely_pain_points: List[str] = Field(
        default_factory=list,
        description="Anticipated business or technical challenges mapped to our solution.",
    )
    suggested_talk_tracks: List[str] = Field(
        default_factory=list,
        description="Targeted conversation starters and value propositions from sales playbooks.",
    )
    objection_handling_notes: List[str] = Field(
        default_factory=list,
        description="Anticipated buyer objections and recommended response guidance.",
    )
    source_urls: List[str] = Field(
        default_factory=list,
        description="Reference URLs and source materials used to compile the brief.",
    )


class FactCheckResult(BaseModel):
    """Verification assessment for a specific factual claim in an AccountBrief."""

    claim: str = Field(..., description="The factual statement or assertion being verified.")
    status: Literal["directly_supported", "reasonable_inference", "unsupported"] = Field(
        default="directly_supported",
        description="Verification category: directly_supported (explicit quote), reasonable_inference (logically follows from grounded facts), or unsupported (genuine fabrication).",
    )
    supported: bool = Field(
        default=True,
        description="True if directly_supported or reasonable_inference, False if unsupported.",
    )
    supporting_evidence: Optional[str] = Field(
        default=None,
        description="Direct snippet or quote from the source context supporting or refuting the claim.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score in the verification judgment.",
    )


class FactCheckedBrief(BaseModel):
    """Final verified AccountBrief package with per-claim audit results and faithfulness score."""

    brief: AccountBrief = Field(..., description="The synthesized account brief.")
    fact_checks: List[FactCheckResult] = Field(
        default_factory=list,
        description="Detailed verification results for all audited claims.",
    )
    overall_faithfulness_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Proportion of verified claims supported by source evidence (0.0 to 1.0).",
    )
    flagged_claims: List[str] = Field(
        default_factory=list,
        description="List of claims that failed fact-checking (unsupported or hallucinated).",
    )

