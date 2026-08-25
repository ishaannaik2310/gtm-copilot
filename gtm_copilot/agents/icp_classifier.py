"""ICP Classifier Agent for evaluating target accounts against internal sales playbook criteria."""

from typing import Any, Dict, List, Optional
import logging

from gtm_copilot.agents.base import BaseAgent
from gtm_copilot.llm import LLMProvider, extract_json, get_default_llm_provider
from gtm_copilot.models import ICPClassification, ResearchOutput
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.reranker import Reranker

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert B2B ICP Qualification and Lead Scoring Analyst. "
    "Your task is to evaluate target company signals against internal Ideal Customer Profile (ICP) "
    "criteria defined in our internal sales playbooks. "
    "Ground your evaluation strictly on the provided company signals and playbook rules. "
    "Do not invent criteria or assumptions not supported by the context."
)


class ICPClassifierAgent(BaseAgent):
    """Agent that classifies target accounts against internal ICP criteria."""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
        reranker: Optional[Reranker] = None,
    ):
        """Initialize ICPClassifierAgent.

        Args:
            llm_provider: LLM provider implementation. Defaults to default provider.
            hybrid_retriever: Optional hybrid retriever for querying playbook ICP criteria.
            reranker: Optional cross-encoder reranker for ranking criteria chunks.
        """
        super().__init__(name="icp_classifier_agent")
        self.llm_provider = llm_provider or get_default_llm_provider()
        self.hybrid_retriever = hybrid_retriever
        self.reranker = reranker

    def retrieve_icp_criteria(self, query: str = "ideal customer profile ICP criteria company size stage revenue") -> List[str]:
        """Retrieve relevant ICP criteria from internal playbooks.

        Args:
            query: Search query for finding ICP guidelines.

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
            logger.warning("Failed to retrieve playbook ICP criteria: %s", e)
            return []

    def build_prompt(
        self,
        research: ResearchOutput,
        playbook_criteria: List[str],
    ) -> str:
        """Build prompt for LLM to classify ICP fit.

        Args:
            research: Extracted target company signals.
            playbook_criteria: Retrieved playbook ICP definitions.

        Returns:
            Formatted prompt string.
        """
        products_str = ", ".join(research.products_or_services) if research.products_or_services else "Unknown"
        tech_str = ", ".join(research.notable_tech_or_tools_mentioned) if research.notable_tech_or_tools_mentioned else "None noted"
        news_str = "; ".join(research.recent_news_or_signals) if research.recent_news_or_signals else "None noted"
        playbook_str = "\n\n---\n\n".join(playbook_criteria) if playbook_criteria else "No explicit playbook criteria provided."

        prompt = f"""Evaluate the target company against our internal Ideal Customer Profile (ICP) criteria and return a JSON object.

### Target Company Research Signals:
- Company Name: {research.company_name or 'Unknown'}
- Industry: {research.industry or 'Unknown'}
- Products / Services: {products_str}
- Apparent Size / Stage Signals: {research.apparent_company_size_signals or 'Unknown'}
- Notable Tech / Tools: {tech_str}
- Recent News / Signals: {news_str}

### Internal Playbook ICP Criteria:
{playbook_str}

### Instructions:
1. Compare the company's signals against the playbook's specific ICP requirements (stage, employee count, ARR, industry, tech stack).
2. Determine fit_label:
   - "strong_fit": Meets primary ICP criteria (e.g. stage, size, and vertical match).
   - "possible_fit": Partially aligns or ambiguous size/stage signals with good vertical alignment.
   - "poor_fit": Clear mismatch with key criteria (e.g. outside target market, incompatible size/stage).
3. Assign a fit_score between 0.0 (no fit) and 1.0 (perfect fit).
4. List matched_criteria and mismatched_criteria as concise strings.
5. Provide a clear rationale explaining the fit determination.

### Required JSON Output Format:
```json
{{
  "fit_score": 0.85,
  "fit_label": "strong_fit",
  "rationale": "Explanation of alignment and gaps against playbook criteria...",
  "matched_criteria": [
    "Target Stage: Series B-D high growth",
    "Vertical: B2B Enterprise SaaS"
  ],
  "mismatched_criteria": []
}}
```
"""
        return prompt

    async def run(self, input: ResearchOutput) -> ICPClassification:
        """Evaluate and classify the target account against internal ICP rules.

        Args:
            input: ResearchOutput payload from the Research Agent.

        Returns:
            ICPClassification model.
        """
        try:
            # 1. Retrieve ICP guidelines from internal knowledge base
            criteria_chunks = self.retrieve_icp_criteria()

            # 2. Build prompt
            prompt = self.build_prompt(input, criteria_chunks)

            # 3. Query LLM
            llm_response = await self.llm_provider.complete(prompt=prompt, system=SYSTEM_PROMPT)

            # 4. Parse JSON
            data = extract_json(llm_response)

            fit_label = data.get("fit_label", "possible_fit")
            if fit_label not in ("strong_fit", "possible_fit", "poor_fit", "unknown"):
                fit_label = "possible_fit"

            raw_score = data.get("fit_score")
            fit_score: Optional[float] = None
            if raw_score is not None:
                try:
                    fit_score = max(0.0, min(1.0, float(raw_score)))
                except (ValueError, TypeError):
                    fit_score = None

            rationale = str(data.get("rationale") or "ICP evaluation completed.")
            matched = [str(x) for x in data.get("matched_criteria", []) if isinstance(x, (str, int, float))]
            mismatched = [str(x) for x in data.get("mismatched_criteria", []) if isinstance(x, (str, int, float))]

            return ICPClassification(
                fit_score=fit_score,
                fit_label=fit_label,
                rationale=rationale,
                matched_criteria=matched,
                mismatched_criteria=mismatched,
            )

        except Exception as e:
            err_msg = f"ICP classification failed: {str(e) or repr(e)}"
            logger.error(err_msg)
            return ICPClassification(
                fit_score=None,
                fit_label="unknown",
                rationale=err_msg,
                matched_criteria=[],
                mismatched_criteria=[],
            )
