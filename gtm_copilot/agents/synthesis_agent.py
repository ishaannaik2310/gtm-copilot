"""Synthesis Agent for compiling grounded Account Intelligence Briefs."""

from typing import Any, Dict, List, Optional
import logging

from gtm_copilot.agents.base import BaseAgent
from gtm_copilot.llm import LLMProvider, extract_json, get_default_llm_provider
from gtm_copilot.models import AccountBrief, ICPClassification, ResearchOutput
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.reranker import Reranker

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert B2B Sales Strategist and Account Intelligence Synthesizer. "
    "Your mission is to synthesize an actionable, high-impact Account Brief for sales and GTM teams. "
    "You must strictly distinguish between: "
    "(1) The TARGET COMPANY'S OWN BUSINESS PAIN POINTS (inferred from their industry, scale, and products), and "
    "(2) OUR SALES PLAYBOOK'S VALUE PROPOSITIONS & OBJECTION REBUTTALS (which belong strictly in suggested_talk_tracks and objection_handling_notes). "
    "Never populate likely_pain_points with buyer objections to adopting our software."
)


class SynthesisAgent(BaseAgent):
    """Agent that compiles structured Account Briefs combining research, ICP fit, and playbook messaging."""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
        reranker: Optional[Reranker] = None,
    ):
        """Initialize SynthesisAgent.

        Args:
            llm_provider: LLM provider implementation. Defaults to default provider.
            hybrid_retriever: Optional retriever for fetching relevant playbook talk tracks and objections.
            reranker: Optional reranker for scoring playbook chunks.
        """
        super().__init__(name="synthesis_agent")
        self.llm_provider = llm_provider or get_default_llm_provider()
        self.hybrid_retriever = hybrid_retriever
        self.reranker = reranker

    def retrieve_playbook_context(self, query: str = "value proposition talk tracks objection handling sales strategy") -> List[str]:
        """Retrieve relevant playbook guidance on messaging, talk tracks, and objection handling.

        Args:
            query: Search query for finding playbook messaging.

        Returns:
            List of relevant text snippets from playbooks.
        """
        if not self.hybrid_retriever:
            return []

        try:
            chunks = self.hybrid_retriever.retrieve(
                query=query,
                top_k=5,
                filter_source_type="playbook",
            )
            if self.reranker and chunks:
                chunks = self.reranker.rerank(query=query, chunks=chunks, top_k=3)
            return [c.text for c in chunks]
        except Exception as e:
            logger.warning("Failed to retrieve playbook messaging context: %s", e)
            return []

    def build_prompt(
        self,
        research: ResearchOutput,
        icp: ICPClassification,
        playbook_snippets: List[str],
    ) -> str:
        """Construct prompt for AccountBrief synthesis.

        Args:
            research: Extracted research facts.
            icp: ICP evaluation result.
            playbook_snippets: Retrieved sales playbook context.

        Returns:
            Formatted prompt string.
        """
        products_str = ", ".join(research.products_or_services) if research.products_or_services else "Unknown"
        tech_str = ", ".join(research.notable_tech_or_tools_mentioned) if research.notable_tech_or_tools_mentioned else "None noted"
        news_str = "; ".join(research.recent_news_or_signals) if research.recent_news_or_signals else "None noted"
        matched_str = ", ".join(icp.matched_criteria) if icp.matched_criteria else "None"
        mismatched_str = ", ".join(icp.mismatched_criteria) if icp.mismatched_criteria else "None"
        playbook_str = "\n\n---\n\n".join(playbook_snippets) if playbook_snippets else "No explicit playbook messaging provided."

        prompt = f"""Synthesize a complete, grounded B2B Account Brief for sales reps based on the provided company signals, ICP assessment, and sales playbook guidelines.

### Target Company Facts:
- Name: {research.company_name or 'Unknown'}
- Industry: {research.industry or 'Unknown'}
- Products & Services: {products_str}
- Size & Stage Signals: {research.apparent_company_size_signals or 'Unknown'}
- Notable Tech & Tools: {tech_str}
- Recent News & Signals: {news_str}
- Source URLs: {", ".join(research.source_urls) if research.source_urls else "N/A"}

### ICP Classification:
- Fit Label: {icp.fit_label}
- Fit Score: {icp.fit_score if icp.fit_score is not None else 'Unknown'}
- Rationale: {icp.rationale}
- Matched Criteria: {matched_str}
- Mismatched Criteria: {mismatched_str}

### Internal Sales Playbook Context (Value Props, Talk Tracks, Objection Handling):
{playbook_str}

### Instructions:
1. Executive Summary: Write a crisp 2-4 sentence narrative summarizing the company's core business, their market position, and our strategic fit.
2. Key Products / Services: List their primary products or platform offerings extracted from the research facts.
3. Likely Pain Points (TARGET COMPANY SPECIFIC): Identify 2-4 operational, technical, or scaling challenges that the TARGET COMPANY experiences in running their own business/product (inferred strictly from their industry, scale, product complexity, and tech stack).
   * CRITICAL RULE: likely_pain_points MUST describe problems the target company faces in their own market/operations. NEVER copy buyer objections to adopting our tool (e.g. do NOT write 'concerned about AI hallucinations' or 'data security when adopting AI software' under likely_pain_points).
4. Suggested Talk Tracks: Provide 2-4 conversation openers and value propositions directly connecting our solution to their pain points, adapted from the playbook's value props.
5. Objection Handling Notes: Provide 2-3 anticipated buyer objections (e.g. build vs buy, security/compliance concerns, tool fatigue) with concise rebuttal points drawn from the playbook's objection handling guidance.
6. Grounding Requirement: Ensure every detail is traceable to the facts and playbook context provided above.

### Required JSON Output Format:
```json
{{
  "company_name": "{research.company_name or 'Company'}",
  "industry": "{research.industry or 'Technology'}",
  "executive_summary": "Crisp overview of company business and strategic alignment...",
  "key_products_or_services": [
    "Product 1",
    "Product 2"
  ],
  "likely_pain_points": [
    "Target company business/scaling challenge 1 (e.g. managing cross-app collaboration sprawl)...",
    "Target company technical/operational challenge 2..."
  ],
  "suggested_talk_tracks": [
    "Talk track 1 highlighting relevant value prop...",
    "Talk track 2..."
  ],
  "objection_handling_notes": [
    "Objection: '...' -> Response: '...'",
    "Objection: '...' -> Response: '...'"
  ],
  "source_urls": {research.source_urls if research.source_urls else ["https://example.com"]}
}}
```
"""
        return prompt

    async def run(
        self,
        research_output: ResearchOutput,
        icp_classification: Optional[ICPClassification] = None,
    ) -> AccountBrief:
        """Synthesize an AccountBrief from research facts and ICP evaluation.

        Args:
            research_output: Output from the Research Agent.
            icp_classification: Output from the ICP Classifier Agent (optional).

        Returns:
            Structured AccountBrief.

        Raises:
            RuntimeError: If LLM generation or parsing fails.
        """
        # If ICP classification was omitted, use an unknown placeholder
        icp = icp_classification or ICPClassification(
            fit_score=None,
            fit_label="unknown",
            rationale="ICP classification was not provided.",
            matched_criteria=[],
            mismatched_criteria=[],
        )

        try:
            # 1. Retrieve playbook messaging & objections
            playbook_snippets = self.retrieve_playbook_context()

            # 2. Build prompt
            prompt = self.build_prompt(
                research=research_output,
                icp=icp,
                playbook_snippets=playbook_snippets,
            )

            # 3. Query LLM
            llm_response = await self.llm_provider.complete(prompt=prompt, system=SYSTEM_PROMPT)

            # 4. Parse JSON
            data = extract_json(llm_response)

            def ensure_list(val: Any) -> List[str]:
                if isinstance(val, list):
                    return [str(x) for x in val if x]
                if isinstance(val, str) and val.strip():
                    return [val.strip()]
                return []

            company_name = str(data.get("company_name") or research_output.company_name or "Unknown Company")
            industry = data.get("industry") or research_output.industry
            exec_summary = str(data.get("executive_summary") or f"Account intelligence brief for {company_name}.")
            products = ensure_list(data.get("key_products_or_services")) or research_output.products_or_services
            pain_points = ensure_list(data.get("likely_pain_points"))
            talk_tracks = ensure_list(data.get("suggested_talk_tracks"))
            objections = ensure_list(data.get("objection_handling_notes"))
            source_urls = ensure_list(data.get("source_urls")) or research_output.source_urls

            return AccountBrief(
                company_name=company_name,
                industry=industry,
                icp_classification=icp,
                executive_summary=exec_summary,
                key_products_or_services=products,
                likely_pain_points=pain_points,
                suggested_talk_tracks=talk_tracks,
                objection_handling_notes=objections,
                source_urls=source_urls,
            )

        except Exception as e:
            err_msg = f"SynthesisAgent failed to generate AccountBrief: {str(e) or repr(e)}"
            logger.error(err_msg)
            raise RuntimeError(err_msg) from e
