"""Live smoke-test script for end-to-end Account Brief generation."""

import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

import chromadb
from gtm_copilot.ingestion.chunker import chunk_documents
from gtm_copilot.ingestion.loader import load_documents
from gtm_copilot.llm import get_default_llm_provider
from gtm_copilot.models import ResearchInput
from gtm_copilot.orchestrator import generate_account_brief
from gtm_copilot.retrieval.bm25_retriever import BM25Retriever
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.reranker import Reranker
from gtm_copilot.retrieval.vector_store import VectorStore


async def main():
    print("=" * 65)
    print("  GTM Ops Copilot - Full Account Brief Generation Pipeline")
    print("=" * 65)

    # 1. Ingest internal knowledge base
    print("\n[1/4] Ingesting internal knowledge base (playbooks + accounts)...")
    docs = load_documents()
    print(f"      Loaded {len(docs)} documents.")

    chunks = chunk_documents(docs, chunk_size=300, chunk_overlap=40)
    print(f"      Generated {len(chunks)} chunks.")

    chroma_client = chromadb.EphemeralClient()
    vector_store = VectorStore(
        collection_name="account_brief_smoke_test",
        client=chroma_client,
    )
    bm25 = BM25Retriever()
    hybrid = HybridRetriever(vector_store=vector_store, bm25_retriever=bm25, rrf_k=60)
    hybrid.index(chunks)
    reranker = Reranker()

    llm_provider = get_default_llm_provider()

    # 2. Setup input
    company_name = sys.argv[1] if len(sys.argv) > 1 else "Notion"
    url = sys.argv[2] if len(sys.argv) > 2 else "https://www.notion.so"
    test_input = ResearchInput(company_name=company_name, url=url)

    print(f"\n[2/4] Executing 4-Agent Pipeline for: {test_input.company_name} ({test_input.url})...")
    print("      Stage 1: ResearchAgent (Web scrape + RAG)")
    print("      Stage 2: ICPClassifierAgent (Playbook ICP qualification)")
    print("      Stage 3: SynthesisAgent (Actionable AccountBrief generation)")
    print("      Stage 4: FactCheckAgent (Claim-level source verification)\n")

    result = await generate_account_brief(
        research_input=test_input,
        hybrid_retriever=hybrid,
        reranker=reranker,
        llm_provider=llm_provider,
    )

    # 3. Output results
    print("=" * 65)
    print("  FACT-CHECKED ACCOUNT BRIEF (JSON)")
    print("=" * 65)
    print(json.dumps(result.model_dump(), indent=2))

    print("\n" + "=" * 65)
    print(f"  FAITHFULNESS SCORE: {result.overall_faithfulness_score * 100:.1f}%")
    print(f"  TOTAL CLAIMS AUDITED: {len(result.fact_checks)}")
    print(f"  FLAGGED / UNSUPPORTED CLAIMS: {len(result.flagged_claims)}")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
