"""Outreach Agent for generating personalized, battlecard-aligned sales email sequences."""

from typing import Any, Dict, List, Optional
import json
import logging

from gtm_copilot.agents.base import BaseAgent
from gtm_copilot.llm import LLMProvider, extract_json, get_default_llm_provider
from gtm_copilot.models import (
    EmailVariant,
    FollowUpVariant,
    OutreachInput,
    OutreachOutput,
)
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.reranker import Reranker

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert Enterprise Sales Development & Outbound Copywriting Specialist. "
    "Your mission is to craft highly personalized, credible, and conversion-oriented cold outreach email sequences "
    "for B2B sales representatives. "
    "You must adhere to strict factual grounding: every company attribute, pain point, product reference, "
    "and value proposition mentioned in your emails must be traceable directly to the provided Account Brief or "
    "internal sales playbooks. Never fabricate prospect details, company news, or ungrounded statistics. "
    "Always output valid, well-formed JSON matching the requested schema."
)


class OutreachAgent(BaseAgent):
    """Agent that generates personalized email sequences and follow-ups grounded in AccountBriefs and sales playbooks."""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
        reranker: Optional[Reranker] = None,
    ):
        """Initialize OutreachAgent.

        Args:
            llm_provider: LLM provider implementation.
            hybrid_retriever: Hybrid retriever for querying sales playbooks.
            reranker: Cross-encoder reranker for precision snippet ranking.
        """
        super().__init__(name="outreach_agent")
        self.llm_provider = llm_provider or get_default_llm_provider()
        self.hybrid_retriever = hybrid_retriever
        self.reranker = reranker

    def retrieve_playbook_context(
        self, query: str = "sales outreach email messaging tone objection value proposition"
    ) -> List[str]:
        """Retrieve relevant sales playbook snippets for outreach messaging and tone guidance."""
        if not self.hybrid_retriever:
            return []

        try:
            chunks = self.hybrid_retriever.retrieve(query, top_k=6, filter_source_type="playbook")
            if self.reranker and chunks:
                chunks = self.reranker.rerank(query, chunks, top_k=4)
            return [c.text for c in chunks]
        except Exception as e:
            logger.warning("Error retrieving playbook context for outreach: %s", e)
            return []

    def build_prompt(self, input: OutreachInput, playbook_snippets: List[str]) -> str:
        """Construct the prompt guiding the LLM to generate grounded outreach sequences."""
        brief = input.account_brief

        brief_context = {
            "company_name": brief.company_name,
            "industry": brief.industry,
            "icp_fit_label": brief.icp_classification.fit_label,
            "icp_rationale": brief.icp_classification.rationale,
            "executive_summary": brief.executive_summary,
            "key_products_or_services": brief.key_products_or_services,
            "likely_pain_points": brief.likely_pain_points,
            "suggested_talk_tracks": brief.suggested_talk_tracks,
            "objection_handling_notes": brief.objection_handling_notes,
        }

        contact_info = {
            "contact_name": input.contact_name or "None (Company-level outreach)",
            "contact_role": input.contact_role or "None (General sales persona)",
            "contact_notes": input.contact_linkedin_or_notes or "None provided",
        }

        playbook_text = (
            "\n\n---\n".join(playbook_snippets)
            if playbook_snippets
            else "No specific playbook snippets retrieved."
        )

        return f"""Generate a personalized outbound sales email sequence for the following target account.

### TARGET ACCOUNT BRIEF (GROUND TRUTH):
{json.dumps(brief_context, indent=2)}

### PROSPECT CONTACT CONTEXT:
{json.dumps(contact_info, indent=2)}

### INTERNAL SALES PLAYBOOK GUIDANCE:
{playbook_text}

---

### STRICT OUTREACH GENERATION RULES:
1. **Factual Grounding**: Every company fact, pain point, product mention, and value proposition MUST be grounded in the provided Account Brief or Playbook Guidance. Do NOT invent fictional metrics, false case studies, or unverified claims.
2. **Contact Identity**: If `contact_name` is missing or 'None', craft high-impact company-level/role-level cold emails without inventing a fake human name (set `"contact_name": null` in the JSON). If `contact_name` is provided, personalize greetings accordingly.
3. **Email Variants (3-5 variants)**:
   - Provide 3 to 5 initial cold email variants with distinct tactical tones (e.g. "direct", "consultative", "curiosity-driven", "problem-agitation").
   - Each variant must include a concise, punchy `subject` line and a brief, compelling `body` (under 150 words per email).
4. **Follow-Up Sequence (2-3 touches)**:
   - Provide 2 to 3 progressive follow-up emails with suggested spacing in `send_after_days` (e.g. 3 days, 7 days) and `sequence_position` (1, 2, 3).
5. **Personalization Notes**:
   - Explicitly list 2-4 key triggers, pain points, or recent company signals that were utilized to tailor this outreach.

### OUTPUT JSON SCHEMA:
Return ONLY valid JSON matching this schema:
{{
  "contact_name": "string or null",
  "email_variants": [
    {{
      "subject": "string",
      "body": "string",
      "tone_label": "direct | consultative | curiosity-driven | problem-agitation"
    }}
  ],
  "follow_up_sequence": [
    {{
      "subject": "string",
      "body": "string",
      "send_after_days": 3,
      "sequence_position": 1
    }}
  ],
  "personalization_notes": [
    "string"
  ]
}}
"""

    async def run(self, input: OutreachInput) -> OutreachOutput:
        """Run the OutreachAgent to produce personalized sales email sequences.

        Args:
            input: OutreachInput with target AccountBrief and optional contact details.

        Returns:
            Structured OutreachOutput model.

        Raises:
            RuntimeError: If LLM call or JSON parsing fails (honest error state).
        """
        logger.info(
            "OutreachAgent: Generating personalized outreach for %s (Contact: %s)",
            input.account_brief.company_name,
            input.contact_name or "General",
        )

        playbook_snippets = self.retrieve_playbook_context()
        prompt = self.build_prompt(input, playbook_snippets)

        try:
            llm_response = await self.llm_provider.complete(
                prompt=prompt,
                system=SYSTEM_PROMPT,
            )
        except Exception as e:
            err_msg = f"OutreachAgent LLM completion failed: {e}"
            logger.error(err_msg, exc_info=True)
            raise RuntimeError(err_msg) from e

        try:
            parsed_data = extract_json(llm_response)
            if not parsed_data or not isinstance(parsed_data, dict):
                raise ValueError("Parsed JSON is not a dictionary.")
        except Exception as e:
            err_msg = f"OutreachAgent failed to parse valid JSON from LLM response: {e}"
            logger.error(err_msg)
            raise RuntimeError(err_msg) from e

        # Build source grounding list for traceability
        source_grounding = [
            f"[Account Brief Summary]: {input.account_brief.executive_summary}",
        ]
        for p in input.account_brief.likely_pain_points:
            source_grounding.append(f"[Account Brief Pain Point]: {p}")
        for t in input.account_brief.suggested_talk_tracks:
            source_grounding.append(f"[Account Brief Talk Track]: {t}")
        for s in playbook_snippets:
            source_grounding.append(f"[Playbook Snippet]: {s}")

        try:
            email_variants = [
                EmailVariant(
                    subject=v.get("subject", ""),
                    body=v.get("body", ""),
                    tone_label=v.get("tone_label", "direct"),
                )
                for v in parsed_data.get("email_variants", [])
            ]

            follow_up_sequence = [
                FollowUpVariant(
                    subject=f.get("subject", ""),
                    body=f.get("body", ""),
                    send_after_days=int(f.get("send_after_days", 3)),
                    sequence_position=int(f.get("sequence_position", idx + 1)),
                )
                for idx, f in enumerate(parsed_data.get("follow_up_sequence", []))
            ]

            if not email_variants:
                raise ValueError("No email_variants generated in outreach output.")

            return OutreachOutput(
                contact_name=parsed_data.get("contact_name") or input.contact_name,
                email_variants=email_variants,
                follow_up_sequence=follow_up_sequence,
                personalization_notes=parsed_data.get("personalization_notes", []),
                source_grounding=source_grounding,
            )
        except Exception as e:
            err_msg = f"OutreachAgent failed to construct OutreachOutput: {e}"
            logger.error(err_msg, exc_info=True)
            raise RuntimeError(err_msg) from e
