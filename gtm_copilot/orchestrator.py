"""Orchestrator coordinating the end-to-end Account Brief and Outreach generation pipelines."""

import asyncio
from typing import Optional
import logging

from gtm_copilot.agents.fact_check_agent import FactCheckAgent
from gtm_copilot.agents.icp_classifier import ICPClassifierAgent
from gtm_copilot.agents.outreach_agent import OutreachAgent
from gtm_copilot.agents.research_agent import ResearchAgent
from gtm_copilot.agents.synthesis_agent import SynthesisAgent
from gtm_copilot.llm import LLMProvider, get_default_llm_provider
from gtm_copilot.models import (
    AgentCallMetrics,
    FactCheckedBrief,
    FactCheckedOutreach,
    OutreachInput,
    PipelineMetrics,
    ResearchInput,
)
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.reranker import Reranker

logger = logging.getLogger(__name__)


class AccountBriefOrchestrator:
    """Coordinates Research -> ICP Classification -> Synthesis -> Fact-Check and Outreach workflows."""

    def __init__(
        self,
        research_agent: Optional[ResearchAgent] = None,
        icp_agent: Optional[ICPClassifierAgent] = None,
        synthesis_agent: Optional[SynthesisAgent] = None,
        fact_check_agent: Optional[FactCheckAgent] = None,
        outreach_agent: Optional[OutreachAgent] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
        reranker: Optional[Reranker] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        """Initialize the multi-agent orchestrator.

        Args:
            research_agent: Agent for company research and web intelligence.
            icp_agent: Agent for ICP qualification and fit scoring.
            synthesis_agent: Agent for synthesizing structured account briefs.
            fact_check_agent: Agent for verifying factual statements in briefs and outreach.
            outreach_agent: Agent for generating personalized outbound sales sequences.
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
        self.outreach_agent = outreach_agent or OutreachAgent(
            llm_provider=provider,
            hybrid_retriever=hybrid_retriever,
            reranker=reranker,
        )

    @staticmethod
    def _aggregate_metrics(all_calls: list[AgentCallMetrics]) -> PipelineMetrics:
        """Aggregate per-call metrics into a PipelineMetrics summary.

        Args:
            all_calls: Flat list of AgentCallMetrics from all participating agents.

        Returns:
            PipelineMetrics with totals computed.
        """
        total_latency = sum(c.latency_seconds for c in all_calls)
        total_prompt = sum(c.prompt_tokens or 0 for c in all_calls)
        total_completion = sum(c.completion_tokens or 0 for c in all_calls)
        total_tok = sum(c.total_tokens or 0 for c in all_calls)

        # Total cost is None if any individual call has no pricing data
        costs = [c.estimated_cost_usd for c in all_calls]
        if all(c is not None for c in costs) and costs:
            total_cost: float | None = round(sum(costs), 8)  # type: ignore[assignment]
        else:
            total_cost = None

        return PipelineMetrics(
            agent_calls=all_calls,
            total_latency_seconds=round(total_latency, 4),
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_tokens=total_tok,
            total_estimated_cost_usd=total_cost,
            call_count=len(all_calls),
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
            Verified FactCheckedBrief (with metrics attached).

        Raises:
            RuntimeError: If synthesis fails.
        """
        logger.info("Starting Account Brief generation for: %s (%s)", input.company_name, input.url)

        # 1. Research Stage
        logger.info("[1/4] Executing ResearchAgent...")
        research_output = await self.research_agent.run(input)

        # 2. ICP Classifier Stage
        logger.info("[2/4] Executing ICPClassifierAgent...")
        icp_classification = await self.icp_agent.run(research_output)

        # 3. Synthesis Stage
        logger.info("[3/4] Executing SynthesisAgent...")
        account_brief = await self.synthesis_agent.run(
            research_output=research_output,
            icp_classification=icp_classification,
        )

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

        # Collect and aggregate metrics from all participating agents
        all_calls: list[AgentCallMetrics] = []
        for agent in (
            self.research_agent,
            self.icp_agent,
            self.synthesis_agent,
            self.fact_check_agent,
        ):
            all_calls.extend(agent.flush_metrics())

        fact_checked_brief.metrics = self._aggregate_metrics(all_calls)

        logger.info(
            "Account Brief generation complete for '%s' (Faithfulness: %.2f, "
            "LLM calls: %d, total tokens: %d, latency: %.2fs)",
            account_brief.company_name,
            fact_checked_brief.overall_faithfulness_score,
            fact_checked_brief.metrics.call_count,
            fact_checked_brief.metrics.total_tokens,
            fact_checked_brief.metrics.total_latency_seconds,
        )
        return fact_checked_brief

    async def generate_outreach(self, input: OutreachInput) -> FactCheckedOutreach:
        """Run the Outreach generation and verification workflow.

        Workflow:
        1. Outreach Agent: synthesizes 3-5 email variants and follow-up sequence.
        2. Fact Check Agent: verifies all assertions in the outreach against AccountBrief and playbooks.

        Args:
            input: Target AccountBrief with optional prospect contact details.

        Returns:
            Verified FactCheckedOutreach package (with metrics attached).

        Raises:
            RuntimeError: If outreach synthesis fails.
        """
        logger.info(
            "Starting Outreach Generation for %s (Contact: %s)",
            input.account_brief.company_name,
            input.contact_name or "General",
        )

        # 1. Outreach Generation Stage
        logger.info("[1/2] Executing OutreachAgent...")
        outreach_output = await self.outreach_agent.run(input)

        # 2. Outreach Fact-Checking Stage
        logger.info("[2/2] Executing FactCheckAgent on Outreach...")
        combined_sources = list(outreach_output.source_grounding)
        for url in input.account_brief.source_urls:
            combined_sources.append(f"[Source URL]: {url}")

        fact_checked_outreach = await self.fact_check_agent.run_outreach(
            outreach=outreach_output,
            source_context=combined_sources,
        )

        # Collect and aggregate metrics from all participating agents
        all_outreach_calls: list[AgentCallMetrics] = []
        for agent in (self.outreach_agent, self.fact_check_agent):
            all_outreach_calls.extend(agent.flush_metrics())

        fact_checked_outreach.metrics = self._aggregate_metrics(all_outreach_calls)

        logger.info(
            "Outreach generation complete for '%s' (Faithfulness: %.2f, "
            "LLM calls: %d, total tokens: %d, latency: %.2fs)",
            input.account_brief.company_name,
            fact_checked_outreach.overall_faithfulness_score,
            fact_checked_outreach.metrics.call_count,
            fact_checked_outreach.metrics.total_tokens,
            fact_checked_outreach.metrics.total_latency_seconds,
        )
        return fact_checked_outreach



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


async def generate_outreach(
    outreach_input: OutreachInput,
    hybrid_retriever: Optional[HybridRetriever] = None,
    reranker: Optional[Reranker] = None,
    llm_provider: Optional[LLMProvider] = None,
) -> FactCheckedOutreach:
    """Convenience helper function to generate a fact-checked Outreach package.

    Args:
        outreach_input: OutreachInput containing target AccountBrief and prospect contact details.
        hybrid_retriever: Optional configured HybridRetriever.
        reranker: Optional configured Reranker.
        llm_provider: Optional configured LLMProvider.

    Returns:
        FactCheckedOutreach instance.
    """
    orchestrator = AccountBriefOrchestrator(
        hybrid_retriever=hybrid_retriever,
        reranker=reranker,
        llm_provider=llm_provider,
    )
    return await orchestrator.generate_outreach(outreach_input)
