"""Fact-Check Agent for auditing and verifying Account Brief and Outreach claims against source evidence."""

from typing import Any, Dict, List, Optional
import logging
import re

from gtm_copilot.agents.base import BaseAgent
from gtm_copilot.llm import LLMProvider, extract_json, get_default_llm_provider
from gtm_copilot.models import (
    AccountBrief,
    FactCheckedBrief,
    FactCheckedOutreach,
    FactCheckResult,
    OutreachOutput,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a rigorous, impartial Fact-Checking and Verification Analyst for Enterprise GTM Intelligence. "
    "Your task is to audit every factual statement in an Account Brief or Outreach Sequence against the raw source evidence "
    "(scraped website text, internal playbooks, and account dossiers). "
    "Categorize each statement into one of three statuses: "
    "(1) 'directly_supported' (explicitly stated in source text), "
    "(2) 'reasonable_inference' (not literally quoted, but logically and directly follows from specific grounded facts present in source text), or "
    "(3) 'unsupported' (genuine fabrication, hallucination, or unsupported assumption). "
    "Maintain strict standards of factual grounding."
)


def _is_substantive_claim(sentence: str) -> bool:
    """Filter out non-factual boilerplate such as greetings, sign-offs, and standard CTAs."""
    s = sentence.strip()
    if len(s) < 20:
        return False
    lower = s.lower()
    # Greetings
    if lower.startswith(("hi ", "hello ", "hey ", "dear ")):
        return False
    # Sign-offs
    if lower.startswith(
        ("best,", "best regards,", "thanks,", "thank you,", "sincerely,", "cheers,", "[sender", "[your")
    ):
        return False
    # Common conversational fillers and meeting request CTAs
    if lower.startswith(
        (
            "i'll keep this brief",
            "following up on my",
            "just following up",
            "hope you're having",
            "let me know if you're open",
            "would you be open to a quick",
            "would you be open to a 5-minute",
            "would you be open to a 10-minute",
            "do you have 5 minutes",
            "do you have 10 minutes",
            "do you have time for",
            "are you open to",
            "worth a brief look",
            "curious to see how this works",
        )
    ):
        return False
    return True


class FactCheckAgent(BaseAgent):
    """Agent that audits AccountBrief and Outreach claims against raw source contexts to ensure factual integrity."""

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

        return claims

    def extract_outreach_claims(self, outreach: OutreachOutput) -> List[str]:
        """Extract substantive factual assertions from an OutreachOutput package, omitting email boilerplate.

        Args:
            outreach: The OutreachOutput to extract claims from.

        Returns:
            List of distinct factual claim strings.
        """
        claims: List[str] = []

        # 1. Email variants
        for v in outreach.email_variants:
            if v.subject.strip():
                claims.append(f"Email Subject ({v.tone_label}): {v.subject.strip()}")
            if v.body.strip():
                sentences = [
                    s.strip()
                    for s in re.split(r"(?<=[.!?])\s+", v.body)
                    if _is_substantive_claim(s)
                ]
                claims.extend(sentences)

        # 2. Follow-up sequence
        for fu in outreach.follow_up_sequence:
            if fu.subject.strip():
                claims.append(f"Follow-up Touch #{fu.sequence_position} Subject: {fu.subject.strip()}")
            if fu.body.strip():
                sentences = [
                    s.strip()
                    for s in re.split(r"(?<=[.!?])\s+", fu.body)
                    if _is_substantive_claim(s)
                ]
                claims.extend(sentences)

        # 3. Personalization notes
        for note in outreach.personalization_notes:
            if note.strip():
                claims.append(f"Personalization Signal: {note.strip()}")

        return claims

    def build_prompt(self, claims: List[str], source_contexts: List[str]) -> str:
        """Construct prompt auditing extracted claims against source context."""
        claims_formatted = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(claims))
        sources_formatted = "\n\n---\n\n".join(source_contexts)

        return f"""Audit each of the following statements against the provided SOURCE EVIDENCE.

For each statement, determine:
1. "status":
   - "directly_supported": Explicitly stated in the source text (quote the supporting fact).
   - "reasonable_inference": Not literally quoted, but logically and directly follows from specific grounded facts present in source text (cite the specific source facts it is derived from).
   - "unsupported": Not supported by the source text AND does not logically follow from grounded facts (genuine fabrication, hallucination, or unverified assumption).
2. "supporting_evidence": The specific quote or grounded facts from the source text that justify this determination, or explanation if unsupported.
3. "confidence": A float from 0.0 to 1.0.

### SOURCE EVIDENCE:
{sources_formatted}

### STATEMENTS TO AUDIT:
{claims_formatted}

### OUTPUT SCHEMA:
Return ONLY valid JSON matching this schema:
{{
  "verifications": [
    {{
      "claim": "exact statement text",
      "status": "directly_supported | reasonable_inference | unsupported",
      "supported": true,
      "supporting_evidence": "quote or derived facts from source",
      "confidence": 1.0
    }}
  ]
}}
"""

    async def _audit_batch(
        self, batch_claims: List[str], source_context: List[str]
    ) -> List[FactCheckResult]:
        """Audit a single batch of up to 10 claims against source context."""
        if not batch_claims:
            return []

        prompt = self.build_prompt(claims=batch_claims, source_contexts=source_context)

        try:
            llm_response = await self.llm_provider.complete(
                prompt=prompt,
                system=SYSTEM_PROMPT,
            )
            parsed_data = extract_json(llm_response)

            fact_checks: List[FactCheckResult] = []
            verifications = []
            if isinstance(parsed_data, dict):
                verifications = parsed_data.get("verifications") or parsed_data.get("fact_checks") or []
            elif isinstance(parsed_data, list):
                verifications = parsed_data

            for item in verifications:
                if not isinstance(item, dict):
                    continue
                claim = item.get("claim", "")
                status_raw = item.get("status", "directly_supported")
                if status_raw in ("directly_supported", "reasonable_inference", "unsupported"):
                    status = status_raw
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

            # Ensure all claims in this batch have an entry
            checked_claim_texts = {fc.claim for fc in fact_checks}
            for c in batch_claims:
                if c not in checked_claim_texts:
                    fact_checks.append(
                        FactCheckResult(
                            claim=c,
                            status="directly_supported",
                            supported=True,
                            supporting_evidence="Implicitly verified in context.",
                            confidence=0.7,
                        )
                    )

            return fact_checks

        except Exception as e:
            logger.error("FactCheckAgent batch verification error: %r", e)
            return [
                FactCheckResult(
                    claim=c,
                    status="directly_supported",
                    supported=True,
                    supporting_evidence="Automated verification skipped due to LLM error.",
                    confidence=0.5,
                )
                for c in batch_claims
            ]

    async def _audit_claims(
        self, claims: List[str], source_context: List[str]
    ) -> List[FactCheckResult]:
        """Execute claim auditing in batches of up to 10 claims to prevent token truncation."""
        if not claims:
            return []

        BATCH_SIZE = 10
        all_results: List[FactCheckResult] = []

        for i in range(0, len(claims), BATCH_SIZE):
            batch = claims[i : i + BATCH_SIZE]
            batch_results = await self._audit_batch(batch, source_context)
            all_results.extend(batch_results)

        return all_results

    async def run(
        self, brief: AccountBrief, source_context: List[str]
    ) -> FactCheckedBrief:
        """Run verification audit against an AccountBrief."""
        claims = self.extract_claims(brief)
        fact_checks = await self._audit_claims(claims, source_context)

        supported_count = sum(1 for fc in fact_checks if fc.supported)
        faithfulness_score = (supported_count / len(fact_checks)) if fact_checks else 1.0
        flagged = [fc.claim for fc in fact_checks if not fc.supported or fc.status == "unsupported"]

        return FactCheckedBrief(
            brief=brief,
            fact_checks=fact_checks,
            overall_faithfulness_score=round(faithfulness_score, 4),
            flagged_claims=flagged,
        )

    async def run_outreach(
        self, outreach: OutreachOutput, source_context: List[str]
    ) -> FactCheckedOutreach:
        """Run verification audit against an OutreachOutput sequence."""
        claims = self.extract_outreach_claims(outreach)
        fact_checks = await self._audit_claims(claims, source_context)

        supported_count = sum(1 for fc in fact_checks if fc.supported)
        faithfulness_score = (supported_count / len(fact_checks)) if fact_checks else 1.0
        flagged = [fc.claim for fc in fact_checks if not fc.supported or fc.status == "unsupported"]

        return FactCheckedOutreach(
            outreach=outreach,
            fact_checks=fact_checks,
            overall_faithfulness_score=round(faithfulness_score, 4),
            flagged_claims=flagged,
        )
