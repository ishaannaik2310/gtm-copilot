"""Unit tests for FactCheckAgent."""

import json
from typing import Any, Optional
import pytest

from gtm_copilot.agents.fact_check_agent import FactCheckAgent
from gtm_copilot.llm.base import LLMProvider
from gtm_copilot.models import AccountBrief, FactCheckedBrief, ICPClassification


class MockLLMProvider(LLMProvider):
    """Mock LLMProvider returning structured verification checks."""

    def __init__(self, response_text: str):
        self.response_text = response_text

    async def complete(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> str:
        return self.response_text


class MockFailingLLMProvider(LLMProvider):
    """Mock LLMProvider that raises an error."""

    async def complete(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> str:
        raise RuntimeError("Verification error")


@pytest.fixture
def sample_brief():
    return AccountBrief(
        company_name="CloudScale Data Inc",
        industry="DevOps",
        icp_classification=ICPClassification(
            fit_score=0.9,
            fit_label="strong_fit",
            rationale="Good fit.",
            matched_criteria=["Series B"],
            mismatched_criteria=[],
        ),
        executive_summary="CloudScale Data provides automated Kubernetes observability. They raised $42M in Series B.",
        key_products_or_services=["Kubernetes Monitor", "Quantum Telemetry Engine"],
        likely_pain_points=["High cardinality metrics"],
        suggested_talk_tracks=["Talk track 1"],
        objection_handling_notes=["Note 1"],
        source_urls=["https://cloudscaledata.io"],
    )


def test_fact_check_extract_claims(sample_brief):
    agent = FactCheckAgent(llm_provider=MockLLMProvider("{}"))
    claims = agent.extract_claims(sample_brief)

    assert len(claims) >= 3
    assert any("Kubernetes observability" in c for c in claims)
    assert any("Quantum Telemetry Engine" in c for c in claims)


@pytest.mark.asyncio
async def test_fact_check_all_supported(sample_brief):
    llm_payload = {
        "fact_checks": [
            {
                "claim": "CloudScale Data provides automated Kubernetes observability.",
                "status": "directly_supported",
                "supported": True,
                "supporting_evidence": "Found in website homepage text.",
                "confidence": 0.98,
            },
            {
                "claim": "They raised $42M in Series B.",
                "status": "directly_supported",
                "supported": True,
                "supporting_evidence": "Confirmed in news signals.",
                "confidence": 0.95,
            },
        ]
    }
    mock_llm = MockLLMProvider(response_text=f"```json\n{json.dumps(llm_payload)}\n```")
    agent = FactCheckAgent(llm_provider=mock_llm)

    source_context = [
        "CloudScale Data offers automated Kubernetes observability and raised $42M Series B."
    ]
    result = await agent.run(brief=sample_brief, source_context=source_context)

    assert isinstance(result, FactCheckedBrief)
    assert result.overall_faithfulness_score >= 0.9
    assert len(result.flagged_claims) == 0


@pytest.mark.asyncio
async def test_fact_check_reasonable_inference_treated_as_supported(sample_brief):
    llm_payload = {
        "fact_checks": [
            {
                "claim": "CloudScale Data provides automated Kubernetes observability.",
                "status": "directly_supported",
                "supported": True,
                "supporting_evidence": "Found in website homepage text.",
                "confidence": 0.98,
            },
            {
                "claim": "Pain point or challenge: High cardinality metrics",
                "status": "reasonable_inference",
                "supported": True,
                "supporting_evidence": "Inferred from Series B Kubernetes observability telemetry complexity.",
                "confidence": 0.90,
            },
        ]
    }
    mock_llm = MockLLMProvider(response_text=json.dumps(llm_payload))
    agent = FactCheckAgent(llm_provider=mock_llm)

    source_context = ["CloudScale Data offers automated Kubernetes observability at Series B stage."]
    result = await agent.run(brief=sample_brief, source_context=source_context)

    assert result.overall_faithfulness_score == 1.0
    assert len(result.flagged_claims) == 0
    assert any(fc.status == "reasonable_inference" for fc in result.fact_checks)


@pytest.mark.asyncio
async def test_fact_check_with_unsupported_flagged_claim(sample_brief):
    llm_payload = {
        "fact_checks": [
            {
                "claim": "CloudScale Data provides automated Kubernetes observability.",
                "status": "directly_supported",
                "supported": True,
                "supporting_evidence": "Found on site.",
                "confidence": 0.95,
            },
            {
                "claim": "CloudScale Data Inc offers or provides: Quantum Telemetry Engine",
                "status": "unsupported",
                "supported": False,
                "supporting_evidence": "No mention of Quantum Telemetry anywhere in provided sources.",
                "confidence": 0.99,
            },
        ]
    }
    mock_llm = MockLLMProvider(response_text=json.dumps(llm_payload))
    agent = FactCheckAgent(llm_provider=mock_llm)

    source_context = ["CloudScale Data offers automated Kubernetes observability."]
    result = await agent.run(brief=sample_brief, source_context=source_context)

    assert result.overall_faithfulness_score < 1.0
    assert len(result.flagged_claims) == 1
    assert "Quantum Telemetry Engine" in result.flagged_claims[0]


@pytest.mark.asyncio
async def test_fact_check_empty_claims():
    empty_brief = AccountBrief(
        company_name="Acme",
        icp_classification=ICPClassification(
            fit_score=0.5,
            fit_label="possible_fit",
            rationale="Rationale",
            matched_criteria=[],
            mismatched_criteria=[],
        ),
        executive_summary="",
        key_products_or_services=[],
        likely_pain_points=[],
        suggested_talk_tracks=[],
        objection_handling_notes=[],
        source_urls=[],
    )
    agent = FactCheckAgent(llm_provider=MockLLMProvider("{}"))
    result = await agent.run(brief=empty_brief, source_context=[])

    assert result.overall_faithfulness_score == 1.0
    assert len(result.fact_checks) == 0
    assert len(result.flagged_claims) == 0


@pytest.mark.asyncio
async def test_fact_check_llm_exception_fallback(sample_brief):
    mock_llm = MockFailingLLMProvider()
    agent = FactCheckAgent(llm_provider=mock_llm)

    result = await agent.run(brief=sample_brief, source_context=["Some context"])

    assert isinstance(result, FactCheckedBrief)
    assert result.brief == sample_brief


def test_fact_check_extract_outreach_claims():
    from gtm_copilot.models import EmailVariant, FollowUpVariant, OutreachOutput

    outreach = OutreachOutput(
        contact_name="Alex",
        email_variants=[
            EmailVariant(
                subject="Accelerating Kubernetes monitoring",
                body="Alex,\n\nCloudScale Data provides automated Kubernetes observability for containerized environments.\n\nIs there a good time to connect next Tuesday?\n\nBest,\n[Sender Name]",
                tone_label="direct",
            )
        ],
        follow_up_sequence=[
            FollowUpVariant(
                subject="Re: Accelerating Kubernetes monitoring",
                body="Alex,\n\nOur platform automates telemetry synthesis and incident triage in under 60 seconds.\n\nWorth a brief 10-minute chat?",
                send_after_days=3,
                sequence_position=1,
            )
        ],
        personalization_notes=["Targeted Kubernetes Monitor product."],
        source_grounding=["Source 1"],
    )

    agent = FactCheckAgent(llm_provider=MockLLMProvider("{}"))
    claims = agent.extract_outreach_claims(outreach)

    assert len(claims) == 2
    assert any("Kubernetes observability" in c for c in claims)
    assert any("telemetry synthesis" in c for c in claims)
    # Ensure greetings, questions, sign-offs, and personalization notes are all excluded
    assert not any(c.startswith("Alex,") for c in claims)
    assert not any("connect next Tuesday" in c for c in claims)
    assert not any("Worth a brief" in c for c in claims)
    assert not any("Personalization Signal" in c for c in claims)
    assert not any("Sender Name" in c for c in claims)


@pytest.mark.asyncio
async def test_fact_check_outreach_supported():
    from gtm_copilot.models import EmailVariant, FollowUpVariant, OutreachOutput, FactCheckedOutreach

    outreach = OutreachOutput(
        contact_name="Alex",
        email_variants=[
            EmailVariant(
                subject="Cut incident prep time",
                body="CloudScale Data delivers automated Kubernetes observability to Series B high-growth teams.",
                tone_label="direct",
            )
        ],
        follow_up_sequence=[
            FollowUpVariant(
                subject="Re: Cut incident prep time",
                body="Following up regarding our telemetry integration.",
                send_after_days=3,
                sequence_position=1,
            )
        ],
        personalization_notes=["CloudScale Series B data stack"],
        source_grounding=["CloudScale Data delivers automated Kubernetes observability."],
    )

    llm_payload = {
        "verifications": [
            {
                "claim": "CloudScale Data delivers automated Kubernetes observability to Series B high-growth teams.",
                "status": "directly_supported",
                "supported": True,
                "supporting_evidence": "Found in source text.",
                "confidence": 0.99,
            }
        ]
    }

    mock_llm = MockLLMProvider(response_text=json.dumps(llm_payload))
    agent = FactCheckAgent(llm_provider=mock_llm)

    result = await agent.run_outreach(
        outreach=outreach,
        source_context=["CloudScale Data delivers automated Kubernetes observability to Series B high-growth teams."],
    )

    assert isinstance(result, FactCheckedOutreach)
    assert result.overall_faithfulness_score == 1.0
    assert len(result.flagged_claims) == 0

