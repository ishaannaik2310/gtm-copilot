"""FastAPI application exposing GTM Ops Copilot account brief and outreach generation endpoints."""

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
import logging
import os

import chromadb
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from gtm_copilot.ingestion.chunker import chunk_documents
from gtm_copilot.ingestion.loader import load_documents
from gtm_copilot.llm import get_default_llm_provider
from gtm_copilot.models import (
    AccountBrief,
    FactCheckedBrief,
    FactCheckedOutreach,
    OutreachInput,
    ResearchInput,
)
from gtm_copilot.orchestrator import AccountBriefOrchestrator
from gtm_copilot.retrieval.bm25_retriever import BM25Retriever
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.reranker import Reranker
from gtm_copilot.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


class BriefRequest(BaseModel):
    """Request payload for generating an account brief."""

    company_name: Optional[str] = Field(
        default=None,
        description="Target company name.",
        examples=["Notion"],
    )
    url: Optional[str] = Field(
        default=None,
        description="Target company homepage or website URL.",
        examples=["https://www.notion.so"],
    )


class OutreachRequest(BaseModel):
    """Request payload for generating personalized cold outreach sequences."""

    account_brief: AccountBrief = Field(
        ...,
        description="The target AccountBrief to base the outreach on.",
    )
    contact_name: Optional[str] = Field(
        default=None,
        description="Optional prospect contact name.",
    )
    contact_role: Optional[str] = Field(
        default=None,
        description="Optional prospect title or role.",
    )
    contact_linkedin_or_notes: Optional[str] = Field(
        default=None,
        description="Optional unstructured notes or context about the prospect.",
    )


def initialize_shared_orchestrator() -> AccountBriefOrchestrator:
    """Initialize and index the shared RAG knowledge base for the API server."""
    logger.info("Initializing knowledge base indexing for FastAPI backend...")
    docs = load_documents()
    chunks = chunk_documents(docs, chunk_size=300, chunk_overlap=40)

    chroma_client = chromadb.EphemeralClient()
    vector_store = VectorStore(
        collection_name="api_shared_knowledge_base",
        client=chroma_client,
    )
    bm25 = BM25Retriever()
    hybrid = HybridRetriever(vector_store=vector_store, bm25_retriever=bm25, rrf_k=60)
    hybrid.index(chunks)
    reranker = Reranker()
    llm_provider = get_default_llm_provider()

    logger.info("Shared knowledge base initialized with %d chunks.", len(chunks))
    return AccountBriefOrchestrator(
        hybrid_retriever=hybrid,
        reranker=reranker,
        llm_provider=llm_provider,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to initialize shared resources on startup."""
    if not hasattr(app.state, "orchestrator") or app.state.orchestrator is None:
        try:
            app.state.orchestrator = initialize_shared_orchestrator()
        except Exception as e:
            logger.warning("Could not auto-initialize shared orchestrator on startup: %s", e)
            app.state.orchestrator = None
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI(
        title="GTM Ops Copilot API",
        description="AI-driven researched and fact-checked account brief and outreach generation API.",
        version="0.2.0",
        lifespan=lifespan,
    )

    # CORS — read allowed origins from ALLOWED_ORIGINS env var (comma-separated).
    # Defaults to localhost:3000 for local development. MUST be set explicitly in production.
    _raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
    allowed_origins: List[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health", status_code=status.HTTP_200_OK)
    async def health_check() -> Dict[str, str]:
        """Simple health check endpoint."""
        return {"status": "ok"}

    @application.post(
        "/api/brief",
        response_model=FactCheckedBrief,
        status_code=status.HTTP_200_OK,
    )
    async def generate_brief(request: BriefRequest) -> FactCheckedBrief:
        """Generate a fully researched, synthesized, and fact-checked account brief."""
        has_name = bool(request.company_name and request.company_name.strip())
        has_url = bool(request.url and request.url.strip())

        if not has_name and not has_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one of 'company_name' or 'url' must be provided.",
            )

        try:
            research_input = ResearchInput(
                company_name=request.company_name.strip() if request.company_name else None,
                url=request.url.strip() if request.url else None,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        orchestrator: Optional[AccountBriefOrchestrator] = getattr(application.state, "orchestrator", None)
        if orchestrator is None:
            orchestrator = AccountBriefOrchestrator()

        try:
            brief_result = await orchestrator.run(research_input)
            return brief_result
        except Exception as e:
            err_msg = str(e) or repr(e)
            logger.error("Pipeline failure in /api/brief: %s", err_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Account brief generation failed: {err_msg}",
            )

    @application.post(
        "/api/outreach",
        response_model=FactCheckedOutreach,
        status_code=status.HTTP_200_OK,
    )
    async def generate_outreach_endpoint(request: OutreachRequest) -> FactCheckedOutreach:
        """Generate a personalized, battlecard-aligned, and fact-checked outreach sequence."""
        if not request.account_brief.company_name or not request.account_brief.company_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid AccountBrief: 'company_name' must not be empty.",
            )

        outreach_input = OutreachInput(
            account_brief=request.account_brief,
            contact_name=request.contact_name.strip() if request.contact_name else None,
            contact_role=request.contact_role.strip() if request.contact_role else None,
            contact_linkedin_or_notes=request.contact_linkedin_or_notes.strip()
            if request.contact_linkedin_or_notes
            else None,
        )

        orchestrator: Optional[AccountBriefOrchestrator] = getattr(application.state, "orchestrator", None)
        if orchestrator is None:
            orchestrator = AccountBriefOrchestrator()

        try:
            outreach_result = await orchestrator.generate_outreach(outreach_input)
            return outreach_result
        except Exception as e:
            err_msg = str(e) or repr(e)
            logger.error("Pipeline failure in /api/outreach: %s", err_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Outreach generation failed: {err_msg}",
            )

    return application


app = create_app()
