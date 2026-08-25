"""Test script for running the Research Agent end-to-end with real web retrieval and Gemini LLM."""

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
from gtm_copilot.agents.research_agent import ResearchAgent
from gtm_copilot.ingestion.chunker import chunk_documents
from gtm_copilot.ingestion.loader import load_documents
from gtm_copilot.llm import get_default_llm_provider
from gtm_copilot.models import ResearchInput
from gtm_copilot.retrieval.bm25_retriever import BM25Retriever
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.reranker import Reranker
from gtm_copilot.retrieval.vector_store import VectorStore


async def main():
    print("=" * 60)
    print("  GTM Ops Copilot - Research Agent Live Smoke Test")
    print("=" * 60)

    # 1. Load and index internal knowledge base
    print("\n[1/3] Ingesting internal knowledge base (playbooks + accounts)...")
    docs = load_documents()
    print(f"      Loaded {len(docs)} documents.")

    chunks = chunk_documents(docs, chunk_size=300, chunk_overlap=40)
    print(f"      Generated {len(chunks)} chunks.")

    chroma_client = chromadb.EphemeralClient()
    vector_store = VectorStore(
        collection_name="research_agent_test",
        client=chroma_client,
    )
    bm25 = BM25Retriever()
    hybrid = HybridRetriever(vector_store=vector_store, bm25_retriever=bm25, rrf_k=60)
    hybrid.index(chunks)
    reranker = Reranker()

    # 2. Instantiate LLM provider and ResearchAgent
    print("\n[2/3] Initializing GeminiProvider and ResearchAgent...")
    llm_provider = get_default_llm_provider()
    agent = ResearchAgent(
        llm_provider=llm_provider,
        hybrid_retriever=hybrid,
        reranker=reranker,
    )

    # 3. Run research against target input
    test_input = ResearchInput(
        company_name="Notion",
        url="https://www.notion.so",
    )
    print(f"\n[3/3] Executing ResearchAgent for: {test_input.company_name} ({test_input.url})...")
    print("      Fetching live website, retrieving internal context, and prompting Gemini...")

    result = await agent.run(test_input)

    # 4. Display formatted JSON output
    print("\n" + "=" * 60)
    print("  RESEARCH AGENT RESULT (JSON)")
    print("=" * 60)
    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
