"""Script to run the live GTM Copilot pipeline and capture real FactCheckedBrief responses.

Executes the end-to-end AccountBriefOrchestrator, records execution metadata
(timestamp, model name, git commit hash), and saves the unmodified output to
frontend/public/examples/<slug>.json.
"""

import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import chromadb
from gtm_copilot.config import DEFAULT_GEMINI_MODEL
from gtm_copilot.ingestion.chunker import chunk_documents
from gtm_copilot.ingestion.loader import load_documents
from gtm_copilot.llm import get_default_llm_provider
from gtm_copilot.models import FactCheckedBrief, ResearchInput
from gtm_copilot.orchestrator import AccountBriefOrchestrator
from gtm_copilot.retrieval.bm25_retriever import BM25Retriever
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.reranker import Reranker
from gtm_copilot.retrieval.vector_store import VectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("capture_example")


def get_git_commit_hash() -> str:
    """Retrieve current git commit hash."""
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(PROJECT_ROOT))
            .decode("utf-8")
            .strip()
        )
    except Exception as e:
        logger.warning("Could not determine git commit hash: %s", e)
        return "unknown"


async def capture_brief(company_name: str, url: str, slug: str) -> None:
    """Run live AccountBriefOrchestrator and save the unmodified FactCheckedBrief."""
    logger.info("Initializing knowledge base for capture of '%s' (%s)...", company_name, url)

    docs = load_documents()
    chunks = chunk_documents(docs, chunk_size=300, chunk_overlap=40)

    chroma_client = chromadb.EphemeralClient(
        settings=chromadb.config.Settings(anonymized_telemetry=False)
    )
    vector_store = VectorStore(
        collection_name="capture_example_kb",
        client=chroma_client,
    )
    bm25 = BM25Retriever()
    hybrid = HybridRetriever(vector_store=vector_store, bm25_retriever=bm25, rrf_k=60)
    hybrid.index(chunks)
    reranker = Reranker()
    llm_provider = get_default_llm_provider()

    orchestrator = AccountBriefOrchestrator(
        hybrid_retriever=hybrid,
        reranker=reranker,
        llm_provider=llm_provider,
    )

    research_input = ResearchInput(company_name=company_name, url=url)
    logger.info("Executing live pipeline for '%s' (%s)...", company_name, url)

    try:
        brief_result: FactCheckedBrief = await orchestrator.run(research_input)
    except Exception as exc:
        logger.error("Pipeline run failed for '%s': %s", company_name, exc, exc_info=True)
        print(f"\n[ERROR] Pipeline failed for {company_name}: {exc}", file=sys.stderr)
        print("Stopping without writing fallback data.", file=sys.stderr)
        sys.exit(1)

    # Validate output
    if not brief_result.brief or not brief_result.brief.company_name:
        logger.error("Pipeline returned empty brief for '%s'. Stopping.", company_name)
        sys.exit(1)

    git_hash = get_git_commit_hash()
    timestamp = datetime.now(timezone.utc).isoformat()

    # Raw dump
    raw_dict = brief_result.model_dump(mode="json")

    payload = {
        "_metadata": {
            "generated_at": timestamp,
            "model": DEFAULT_GEMINI_MODEL,
            "git_commit": git_hash,
            "faithfulness_score": brief_result.overall_faithfulness_score,
            "company_name": company_name,
            "url": url,
        },
        **raw_dict,
    }

    output_dir = PROJECT_ROOT / "frontend" / "public" / "examples"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{slug}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    logger.info("Saved raw real pipeline output to %s", output_file)
    print(f"\nSUCCESS: Captured real pipeline output for {company_name}")
    print(f"File: {output_file}")
    print(f"Model: {DEFAULT_GEMINI_MODEL}")
    print(f"Commit: {git_hash}")
    print(f"Generated at: {timestamp}")
    print(f"Faithfulness score: {brief_result.overall_faithfulness_score * 100:.1f}%\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture live pipeline execution to example JSON.")
    parser.add_argument("--name", required=True, help="Target company name (e.g. Notion)")
    parser.add_argument("--url", required=True, help="Target company website URL (e.g. https://www.notion.so)")
    parser.add_argument("--slug", required=True, help="Output filename slug (e.g. notion)")

    args = parser.parse_args()
    asyncio.run(capture_brief(company_name=args.name, url=args.url, slug=args.slug))


if __name__ == "__main__":
    main()
