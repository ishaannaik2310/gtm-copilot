"""Live test script for end-to-end Outreach Generation pipeline."""

import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

# 1. Load environment variables from .env
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

import chromadb
from gtm_copilot.ingestion.chunker import chunk_documents
from gtm_copilot.ingestion.loader import load_documents
from gtm_copilot.llm import get_default_llm_provider
from gtm_copilot.models import OutreachInput, ResearchInput
from gtm_copilot.orchestrator import generate_account_brief, generate_outreach
from gtm_copilot.retrieval.bm25_retriever import BM25Retriever
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.reranker import Reranker
from gtm_copilot.retrieval.vector_store import VectorStore


async def main():
    print("=" * 70)
    print("  GTM Ops Copilot - End-to-End Outreach Generation Test")
    print("=" * 70)

    # 2. Ingest and index sample data into HybridRetriever
    print("\n[1/4] Ingesting knowledge base (playbooks + sample accounts)...")
    docs = load_documents()
    print(f"      Loaded {len(docs)} documents.")

    chunks = chunk_documents(docs, chunk_size=300, chunk_overlap=40)
    print(f"      Indexed {len(chunks)} chunks.")

    chroma_client = chromadb.EphemeralClient()
    vector_store = VectorStore(
        collection_name="outreach_test_kb",
        client=chroma_client,
    )
    bm25 = BM25Retriever()
    hybrid = HybridRetriever(vector_store=vector_store, bm25_retriever=bm25, rrf_k=60)
    hybrid.index(chunks)
    reranker = Reranker()

    llm_provider = get_default_llm_provider()

    # 3. Run generate_account_brief() for Notion
    print("\n[2/4] Generating Account Brief for Notion (https://www.notion.so)...")
    research_input = ResearchInput(company_name="Notion", url="https://www.notion.so")
    brief_result = await generate_account_brief(
        research_input=research_input,
        hybrid_retriever=hybrid,
        reranker=reranker,
        llm_provider=llm_provider,
    )
    print(f"      Account Brief generated for '{brief_result.brief.company_name}'.")
    print(f"      Brief Faithfulness Score: {brief_result.overall_faithfulness_score * 100:.1f}%")

    # 4. Call generate_outreach() with the brief + contact details
    print("\n[3/4] Generating Fact-Checked Outreach for Alex Chen (VP of Sales)...")
    outreach_input = OutreachInput(
        account_brief=brief_result.brief,
        contact_name="Alex Chen",
        contact_role="VP of Sales",
        contact_linkedin_or_notes="Focused on expanding Notion's enterprise sales footprint and sales engineering enablement.",
    )

    outreach_result = await generate_outreach(
        outreach_input=outreach_input,
        hybrid_retriever=hybrid,
        reranker=reranker,
        llm_provider=llm_provider,
    )

    # 5. Print full FactCheckedOutreach as formatted JSON
    print("\n" + "=" * 70)
    print("  FACT-CHECKED OUTREACH OUTPUT (JSON)")
    print("=" * 70)
    print(json.dumps(outreach_result.model_dump(), indent=2))

    print("\n" + "=" * 70)
    print(f"  OUTREACH FAITHFULNESS SCORE: {outreach_result.overall_faithfulness_score * 100:.1f}%")
    print(f"  TOTAL OUTREACH CLAIMS AUDITED: {len(outreach_result.fact_checks)}")
    print(f"  FLAGGED / UNSUPPORTED CLAIMS: {len(outreach_result.flagged_claims)}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
