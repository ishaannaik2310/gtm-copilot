"""FastAPI application exposing GTM Ops Copilot account brief and outreach generation endpoints."""

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
import logging
import os
import time

import chromadb
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from gtm_copilot.config import GEMINI_API_KEY, log_gemini_key_status
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
    t_start = time.perf_counter()
    logger.info("Initializing knowledge base indexing for FastAPI backend...")

    t0 = time.perf_counter()
    docs = load_documents()
    chunks = chunk_documents(docs, chunk_size=300, chunk_overlap=40)
    t_docs = time.perf_counter() - t0
    logger.info("Lifespan Phase 1 (Docs & Chunks): %.3fs (%d docs, %d chunks)", t_docs, len(docs), len(chunks))

    t0 = time.perf_counter()
    chroma_client = chromadb.EphemeralClient(
        settings=chromadb.config.Settings(anonymized_telemetry=False)
    )
    vector_store = VectorStore(
        collection_name="api_shared_knowledge_base",
        client=chroma_client,
    )
    t_chroma = time.perf_counter() - t0
    logger.info("Lifespan Phase 2 (Chroma Client & VectorStore): %.3fs", t_chroma)

    t0 = time.perf_counter()
    bm25 = BM25Retriever()
    hybrid = HybridRetriever(vector_store=vector_store, bm25_retriever=bm25, rrf_k=60)
    t_hybrid_setup = time.perf_counter() - t0
    logger.info("Lifespan Phase 3 (BM25 & Hybrid Setup): %.3fs", t_hybrid_setup)

    t0 = time.perf_counter()
    hybrid.index(chunks)
    t_indexing = time.perf_counter() - t0
    logger.info("Lifespan Phase 4 (Hybrid Indexing & Embeddings): %.3fs", t_indexing)

    t0 = time.perf_counter()
    reranker = Reranker()
    t_reranker = time.perf_counter() - t0
    logger.info("Lifespan Phase 5 (Reranker Init): %.3fs", t_reranker)

    t0 = time.perf_counter()
    llm_provider = get_default_llm_provider()
    orchestrator = AccountBriefOrchestrator(
        hybrid_retriever=hybrid,
        reranker=reranker,
        llm_provider=llm_provider,
    )
    t_orch = time.perf_counter() - t0
    logger.info("Lifespan Phase 6 (LLM & Orchestrator Wiring): %.3fs", t_orch)

    total_time = time.perf_counter() - t_start
    logger.info("Shared knowledge base initialized successfully in %.3fs with %d chunks.", total_time, len(chunks))
    return orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to initialize shared resources on startup."""
    log_gemini_key_status(GEMINI_API_KEY)
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
    # Normalizes origins by stripping quotes, whitespace, and trailing slashes.
    _raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
    parsed_origins: List[str] = [
        o.strip().strip("'\"").rstrip("/") for o in _raw_origins.split(",") if o.strip()
    ]
    # Always include standard local development hosts
    for local_origin in ["http://localhost:3000", "http://127.0.0.1:3000"]:
        if local_origin not in parsed_origins:
            parsed_origins.append(local_origin)

    # Permit all Vercel deployment domains (production and preview branches) via regex
    allow_origin_regex = r"^https://.*\.vercel\.app$"

    logger.info("Configured CORS allowed_origins: %s, regex: %s", parsed_origins, allow_origin_regex)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=parsed_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health", status_code=status.HTTP_200_OK)
    async def health_check() -> Dict[str, Any]:
        """Readiness and health check endpoint."""
        orchestrator = getattr(application.state, "orchestrator", None)
        models_loaded = orchestrator is not None
        reranker_enabled = os.getenv("ENABLE_CROSS_ENCODER", "false").lower() in ("true", "1", "yes")
        return {
            "status": "ok",
            "ready": models_loaded,
            "models_loaded": models_loaded,
            "reranker_enabled": reranker_enabled,
        }

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

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("gtm_copilot.api.main:app", host="0.0.0.0", port=port)
