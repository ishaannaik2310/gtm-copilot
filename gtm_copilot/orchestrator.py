"""Orchestrator coordinating the end-to-end Account Brief generation pipeline."""

import asyncio
from typing import Optional
import logging

from gtm_copilot.agents.fact_check_agent import FactCheckAgent
from gtm_copilot.agents.icp_classifier import ICPClassifierAgent
from gtm_copilot.agents.research_agent import ResearchAgent
from gtm_copilot.agents.synthesis_agent import SynthesisAgent
from gtm_copilot.llm import LLMProvider, get_default_llm_provider
from gtm_copilot.models import FactCheckedBrief, ResearchInput
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.reranker import Reranker

logger = logging.getLogger(__name__)


class AccountBriefOrchestrator:
    """Coordinates Research -> ICP Classification -> Synthesis -> Fact-Check workflow."""

    def __init__(
        self,
        research_agent: Optional[ResearchAgent] = None,
        icp_agent: Optional[ICPClassifierAgent] = None,
        synthesis_agent: Optional[SynthesisAgent] = None,
        fact_check_agent: Optional[FactCheckAgent] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
        reranker: Optional[Reranker] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        """Initialize the multi-agent orchestrator.

        Args:
            research_agent: Agent for company research and web intelligence.
            icp_agent: Agent for ICP qualification and fit scoring.
            synthesis_agent: Agent for synthesizing structured account briefs.
            fact_check_agent: Agent for verifying factual statements in briefs.
            hybrid_retriever: Shared hybrid retriever instance.
            reranker: Shared cross-encoder reranker instance.
            llm_provider: Shared LLM provider instance.
        """
        provider = llm_provider or get_default_llm_provider()

        self.research_agent = research_agent or ResearchAgent(
            llm_provider=provider,
            hybrid_retriever=hybrid_retriever,
            reranker=reranker,
        )
        self.icp_agent = icp_agent or ICPClassifierAgent(
            llm_provider=provider,
            hybrid_retriever=hybrid_retriever,
            reranker=reranker,
        )
        self.synthesis_agent = synthesis_agent or SynthesisAgent(
            llm_provider=provider,
            hybrid_retriever=hybrid_retriever,
            reranker=reranker,
        )
        self.fact_check_agent = fact_check_agent or FactCheckAgent(
            llm_provider=provider,
        )

    async def run(self, input: ResearchInput) -> FactCheckedBrief:
        """Run the full 4-stage Account Brief generation pipeline.

        Pipeline Stages:
        1. Research Agent: gathers web facts and internal grounding.
        2. ICP Classifier Agent: scores company signals against playbook rules.
           (If classification fails, gracefully degrades to 'unknown' fit without halting).
        3. Synthesis Agent: compiles grounded Account Brief.
           (If synthesis fails, halts pipeline and raises error rather than inventing fake data).
        4. Fact Check Agent: audits all statements against raw source context.

        Args:
            input: Target company name and/or URL.

        Returns:
            Verified FactCheckedBrief.

        Raises:
            RuntimeError: If synthesis fails.
        """
        logger.info("Starting Account Brief generation for: %s (%s)", input.company_name, input.url)

        # 1. Research Stage
        logger.info("[1/4] Executing ResearchAgent...")
        research_output = await self.research_agent.run(input)

        # Delay to stay within free-tier rate limits
        await asyncio.sleep(2.5)

        # 2. ICP Classifier Stage
        logger.info("[2/4] Executing ICPClassifierAgent...")
        icp_classification = await self.icp_agent.run(research_output)

        # Delay to stay within free-tier rate limits
        await asyncio.sleep(2.5)

        # 3. Synthesis Stage
        logger.info("[3/4] Executing SynthesisAgent...")
        account_brief = await self.synthesis_agent.run(
            research_output=research_output,
            icp_classification=icp_classification,
        )

        # Delay to stay within free-tier rate limits
        await asyncio.sleep(2.5)

        # 4. Fact-Checking Stage
        logger.info("[4/4] Executing FactCheckAgent...")
        combined_sources = list(research_output.raw_context_used)
        try:
            synthesis_snippets = self.synthesis_agent.retrieve_playbook_context()
            for s in synthesis_snippets:
                snippet_entry = f"[Internal Playbook Guidance]:\n{s}"
                if snippet_entry not in combined_sources:
                    combined_sources.append(snippet_entry)
        except Exception as e:
            logger.warning("Could not append synthesis snippets to fact check sources: %s", e)

        fact_checked_brief = await self.fact_check_agent.run(
            brief=account_brief,
            source_context=combined_sources,
        )

        logger.info(
            "Account Brief generation complete for '%s' (Faithfulness Score: %.2f)",
            account_brief.company_name,
            fact_checked_brief.overall_faithfulness_score,
        )
        return fact_checked_brief


async def generate_account_brief(
    research_input: ResearchInput,
    hybrid_retriever: Optional[HybridRetriever] = None,
    reranker: Optional[Reranker] = None,
    llm_provider: Optional[LLMProvider] = None,
) -> FactCheckedBrief:
    """Convenience helper function to generate a fact-checked Account Brief.

    Args:
        research_input: Company name and/or URL.
        hybrid_retriever: Optional configured HybridRetriever.
        reranker: Optional configured Reranker.
        llm_provider: Optional configured LLMProvider.

    Returns:
        FactCheckedBrief instance.
    """
    orchestrator = AccountBriefOrchestrator(
        hybrid_retriever=hybrid_retriever,
        reranker=reranker,
        llm_provider=llm_provider,
    )
    return await orchestrator.run(research_input)
