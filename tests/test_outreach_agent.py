"""Unit tests for OutreachAgent."""

import json
import pytest

from gtm_copilot.agents.outreach_agent import OutreachAgent
from gtm_copilot.llm.base import LLMProvider
from gtm_copilot.models import (
    AccountBrief,
    ICPClassification,
    OutreachInput,
    OutreachOutput,
)


class MockLLMProvider(LLMProvider):
    def __init__(self, response_text: str = "", should_fail: bool = False):
        self.response_text = response_text
        self.should_fail = should_fail
        self.call_count = 0
        self.last_prompt = ""

    async def complete(self, prompt: str, system: str = "") -> str:
        self.call_count += 1
        self.last_prompt = prompt
        if self.should_fail:
            raise RuntimeError("Simulated LLM network failure.")
        return self.response_text


@pytest.fixture
def sample_account_brief():
    return AccountBrief(
        company_name="Acme Health",
        industry="Healthcare Technology",
        icp_classification=ICPClassification(
            fit_score=0.88,
            fit_label="strong_fit",
            rationale="Leading HIPAA-compliant telehealth platform matching Series C target criteria.",
            matched_criteria=["Series C", "150-500 employees", "B2B SaaS"],
            mismatched_criteria=[],
        ),
        executive_summary="Acme Health provides enterprise telehealth workflows trusted by top hospital networks.",
        key_products_or_services=["Telehealth Core", "EHR Sync", "Patient Portal"],
        likely_pain_points=[
            "High pre-call research overhead for reps pitching to diverse clinical buyer personas.",
            "Long sales cycles integrating legacy hospital systems.",
        ],
        suggested_talk_tracks=[
            "Cut prep time from 45 min to 3 min for clinical enterprise sales.",
        ],
        objection_handling_notes=[
            "Objection: EHR security -> Response: SOC 2 Type II and HIPAA compliant.",
        ],
        source_urls=["https://acmehealth.com"],
    )


@pytest.mark.asyncio
async def test_outreach_agent_with_contact_details(sample_account_brief):
    mock_payload = {
        "contact_name": "Sarah Connor",
        "email_variants": [
            {
                "subject": "Quick question on EHR integration deal cycles at Acme Health",
                "body": "Hi Sarah, saw your focus on expanding Acme Health's hospital network footprint. Reps often spend 45+ minutes on manual prep before clinical calls. We automate this into 2-minute verified dossiers.",
                "tone_label": "direct",
            },
            {
                "subject": "Accelerating hospital pipeline for Acme Health",
                "body": "Sarah, given Acme Health's expansion into hospital systems, clinical sales cycles can drag due to complex stakeholder mapping. Would love to share how peers cut research overhead.",
                "tone_label": "consultative",
            },
            {
                "subject": "Telehealth sales velocity",
                "body": "Hi Sarah, how is your team handling pre-call intelligence for clinical buyers across EHR integrations? Thought this might be relevant.",
                "tone_label": "curiosity-driven",
            },
        ],
        "follow_up_sequence": [
            {
                "subject": "Re: Quick question on EHR integration deal cycles",
                "body": "Following up on my note below, Sarah — thought you might find our clinical brief workflow relevant for your AE team.",
                "send_after_days": 3,
                "sequence_position": 1,
            },
            {
                "subject": "One last thought for Acme Health",
                "body": "Sarah, understand if this isn't top priority right now. Leaving a quick link to our case study here if helpful.",
                "send_after_days": 7,
                "sequence_position": 2,
            },
        ],
        "personalization_notes": [
            "Leveraged Acme Health's EHR Sync product and hospital sales cycle challenges.",
            "Addressed Sarah Connor directly as the revenue lead.",
        ],
    }

    mock_llm = MockLLMProvider(response_text=json.dumps(mock_payload))
    agent = OutreachAgent(llm_provider=mock_llm)

    outreach_input = OutreachInput(
        account_brief=sample_account_brief,
        contact_name="Sarah Connor",
        contact_role="VP of Sales",
        contact_linkedin_or_notes="Recently posted about expanding into rural hospital systems.",
    )

    result = await agent.run(outreach_input)

    assert isinstance(result, OutreachOutput)
    assert result.contact_name == "Sarah Connor"
    assert len(result.email_variants) == 3
    assert result.email_variants[0].tone_label == "direct"
    assert len(result.follow_up_sequence) == 2
    assert result.follow_up_sequence[0].send_after_days == 3
    assert len(result.personalization_notes) == 2
    assert len(result.source_grounding) > 0


@pytest.mark.asyncio
async def test_outreach_agent_without_contact_details(sample_account_brief):
    mock_payload = {
        "contact_name": None,
        "email_variants": [
            {
                "subject": "Pre-call research for Acme Health's sales team",
                "body": "Hi team, noticed Acme Health scaling its EHR Sync offering. We help healthtech reps automate deep account prep into 2-minute dossiers.",
                "tone_label": "direct",
            }
        ],
        "follow_up_sequence": [
            {
                "subject": "Re: Pre-call research for Acme Health",
                "body": "Following up on my previous note regarding clinical sales research automation.",
                "send_after_days": 4,
                "sequence_position": 1,
            }
        ],
        "personalization_notes": [
            "Crafted company-level cold outreach focused on Acme Health's EHR Sync product.",
        ],
    }

    mock_llm = MockLLMProvider(response_text=json.dumps(mock_payload))
    agent = OutreachAgent(llm_provider=mock_llm)

    outreach_input = OutreachInput(
        account_brief=sample_account_brief,
        contact_name=None,
        contact_role=None,
    )

    result = await agent.run(outreach_input)

    assert isinstance(result, OutreachOutput)
    assert result.contact_name is None
    assert len(result.email_variants) == 1
    assert result.email_variants[0].subject.startswith("Pre-call research")


@pytest.mark.asyncio
async def test_outreach_agent_llm_exception_failure(sample_account_brief):
    mock_llm = MockLLMProvider(should_fail=True)
    agent = OutreachAgent(llm_provider=mock_llm)

    outreach_input = OutreachInput(account_brief=sample_account_brief)

    with pytest.raises(RuntimeError) as exc_info:
        await agent.run(outreach_input)
    assert "OutreachAgent LLM completion failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_outreach_agent_malformed_json_failure(sample_account_brief):
    mock_llm = MockLLMProvider(response_text="I am not JSON at all.")
    agent = OutreachAgent(llm_provider=mock_llm)

    outreach_input = OutreachInput(account_brief=sample_account_brief)

    with pytest.raises(RuntimeError) as exc_info:
        await agent.run(outreach_input)
    assert "OutreachAgent failed to parse valid JSON" in str(exc_info.value)
