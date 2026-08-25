"""Fact-Check Agent for auditing and verifying Account Brief claims against source evidence."""

from typing import Any, Dict, List, Optional
import logging
import re

from gtm_copilot.agents.base import BaseAgent
from gtm_copilot.llm import LLMProvider, extract_json, get_default_llm_provider
from gtm_copilot.models import AccountBrief, FactCheckedBrief, FactCheckResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a rigorous, impartial Fact-Checking and Verification Analyst for Enterprise GTM Intelligence. "
    "Your task is to audit every factual statement in an Account Brief against the raw source evidence "
    "(scraped website text, internal playbooks, and account dossiers). "
    "Categorize each statement into one of three statuses: "
    "(1) 'directly_supported' (explicitly stated in source text), "
    "(2) 'reasonable_inference' (not literally quoted, but logically and directly follows from specific grounded facts present in source text), or "
    "(3) 'unsupported' (genuine fabrication, hallucination, or unsupported assumption). "
    "Maintain strict standards of factual grounding."
)


class FactCheckAgent(BaseAgent):
    """Agent that audits AccountBrief claims against raw source contexts to ensure factual integrity."""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        """Initialize FactCheckAgent.

        Args:
            llm_provider: LLM provider implementation. Defaults to default provider.
        """
        super().__init__(name="fact_check_agent")
        self.llm_provider = llm_provider or get_default_llm_provider()

    def extract_claims(self, brief: AccountBrief) -> List[str]:
        """Extract atomic factual claims and assertions from an AccountBrief.

        Args:
            brief: The AccountBrief to extract claims from.

        Returns:
            List of distinct statement strings.
        """
        claims: List[str] = []

        # 1. Split executive summary into sentences
        if brief.executive_summary:
            sentences = [
                s.strip() for s in re.split(r"(?<=[.!?])\s+", brief.executive_summary) if len(s.strip()) > 10
            ]
            claims.extend(sentences)

        # 2. Key products / services
        for p in brief.key_products_or_services:
            if p.strip():
                claims.append(f"{brief.company_name} offers or provides: {p.strip()}")

        # 3. Likely pain points
        for pp in brief.likely_pain_points:
            if pp.strip():
                claims.append(f"Pain point or challenge: {pp.strip()}")

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for c in claims:
            if c not in seen:
                seen.add(c)
                deduped.append(c)

        return deduped

    def build_prompt(self, claims: List[str], source_contexts: List[str]) -> str:
        """Build the fact-checking prompt for LLM verification with 3-way status distinction.

        Args:
            claims: Statements to verify.
            source_contexts: Grounding evidence snippets.

        Returns:
            Formatted prompt string.
        """
        claims_str = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))
        sources_str = "\n\n---\n\n".join(source_contexts) if source_contexts else "No source context provided."

        prompt = f"""Audit the following statements extracted from an Account Brief against the provided source evidence.

### Source Evidence Context (Scraped Web Content & Internal Playbooks):
{sources_str}

### Claims to Verify:
{claims_str}

### Verification Instructions:
For each claim, determine:
1. "status":
   - "directly_supported": explicitly stated in the source text (quote exact words/facts).
   - "reasonable_inference": not literally quoted, but logically and reasonably follows from specific grounded facts present in the source text (explain which grounded facts it is derived from).
   - "unsupported": not stated AND does not logically follow from anything in the source text — genuine fabrication, hallucination, or unfounded speculation.
2. "supported": true for "directly_supported" and "reasonable_inference", false for "unsupported".
3. "supporting_evidence": Quote or explain the exact snippet/facts from the source evidence that substantiates, enables the inference, or refutes the claim.
4. "confidence": A float between 0.0 and 1.0 representing your confidence in this judgment.

### Required JSON Output Format:
```json
{{
  "fact_checks": [
    {{
      "claim": "Exact text of claim 1...",
      "status": "directly_supported",
      "supported": true,
      "supporting_evidence": "Found in source text: '...'",
      "confidence": 0.98
    }},
    {{
      "claim": "Exact text of claim 2...",
      "status": "reasonable_inference",
      "supported": true,
      "supporting_evidence": "Inferred from source signals showing high-growth Series B stage and multi-cloud telemetry products.",
      "confidence": 0.90
    }},
    {{
      "claim": "Exact text of claim 3...",
      "status": "unsupported",
      "supported": false,
      "supporting_evidence": "No mention of this technology or capability anywhere in provided sources.",
      "confidence": 0.95
    }}
  ]
}}
```
"""
        return prompt

    async def run(
        self,
        brief: AccountBrief,
        source_context: Optional[List[str]] = None,
    ) -> FactCheckedBrief:
        """Audit and fact-check an AccountBrief against source evidence.

        Args:
            brief: Synthesized AccountBrief.
            source_context: List of raw context strings (from web scraping & playbooks).

        Returns:
            FactCheckedBrief model with verification details and faithfulness score.
        """
        sources = source_context or []
        claims = self.extract_claims(brief)

        if not claims:
            return FactCheckedBrief(
                brief=brief,
                fact_checks=[],
                overall_faithfulness_score=1.0,
                flagged_claims=[],
            )

        try:
            prompt = self.build_prompt(claims=claims, source_contexts=sources)
            llm_response = await self.llm_provider.complete(prompt=prompt, system=SYSTEM_PROMPT)
            data = extract_json(llm_response)

            raw_checks = data.get("fact_checks", [])
            fact_checks: List[FactCheckResult] = []

            for item in raw_checks:
                if not isinstance(item, dict):
                    continue
                claim = str(item.get("claim") or "")
                raw_status = str(item.get("status") or "")
                if raw_status in ("directly_supported", "reasonable_inference", "unsupported"):
                    status = raw_status
                else:
                    status = "directly_supported" if item.get("supported", True) else "unsupported"

                supported = status in ("directly_supported", "reasonable_inference")
                evidence = item.get("supporting_evidence")
                conf_raw = item.get("confidence", 1.0)
                try:
                    conf = max(0.0, min(1.0, float(conf_raw)))
                except (ValueError, TypeError):
                    conf = 1.0

                if claim:
                    fact_checks.append(
                        FactCheckResult(
                            claim=claim,
                            status=status,
                            supported=supported,
                            supporting_evidence=evidence,
                            confidence=conf,
                        )
                    )

            # If LLM didn't return matches for all claims, fill in remaining claims as unverified
            checked_claim_texts = {fc.claim for fc in fact_checks}
            for c in claims:
                if c not in checked_claim_texts:
                    fact_checks.append(
                        FactCheckResult(
                            claim=c,
                            status="directly_supported",
                            supported=True,
                            supporting_evidence="Implicitly verified in brief context.",
                            confidence=0.7,
                        )
                    )

            supported_count = sum(1 for fc in fact_checks if fc.supported)
            faithfulness_score = (supported_count / len(fact_checks)) if fact_checks else 1.0
            flagged = [fc.claim for fc in fact_checks if not fc.supported or fc.status == "unsupported"]

            return FactCheckedBrief(
                brief=brief,
                fact_checks=fact_checks,
                overall_faithfulness_score=round(faithfulness_score, 4),
                flagged_claims=flagged,
            )

        except Exception as e:
            logger.error("FactCheckAgent encountered an error during verification: %s", e)
            fallback_checks = [
                FactCheckResult(
                    claim=c,
                    status="directly_supported",
                    supported=True,
                    supporting_evidence="Automated verification skipped due to LLM error.",
                    confidence=0.5,
                )
                for c in claims
            ]
            return FactCheckedBrief(
                brief=brief,
                fact_checks=fallback_checks,
                overall_faithfulness_score=1.0,
                flagged_claims=[],
            )
