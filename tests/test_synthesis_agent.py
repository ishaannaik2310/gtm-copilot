"""Unit tests for SynthesisAgent."""

import json
from typing import Any, Optional
import pytest

from gtm_copilot.agents.synthesis_agent import SynthesisAgent
from gtm_copilot.llm.base import LLMProvider
from gtm_copilot.models import AccountBrief, Chunk, ICPClassification, ResearchOutput


class MockLLMProvider(LLMProvider):
    """Mock LLMProvider returning structured JSON."""

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.last_prompt: Optional[str] = None
        self.last_system: Optional[str] = None

    async def complete(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> str:
        self.last_prompt = prompt
        self.last_system = system
        return self.response_text


class MockFailingLLMProvider(LLMProvider):
    """Mock LLMProvider that raises an error."""

    async def complete(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> str:
        raise RuntimeError("LLM synthesis error")


class MockRetriever:
    """Mock retriever returning playbook messaging."""

    def retrieve(self, query: str, top_k: int = 5, filter_source_type: Optional[str] = None):
        return [
            Chunk(
                id="c-playbook-messaging",
                document_id="doc-1",
                text="Talk Track: Automate 45 minutes of manual context gathering into a 2-minute actionable brief.",
                metadata={"source_type": "playbook"},
            )
        ]


@pytest.fixture
def sample_inputs():
    research = ResearchOutput(
        company_name="CloudScale Data Inc",
        industry="DevOps / Cloud",
        products_or_services=["Kubernetes Observability"],
        apparent_company_size_signals="Series B stage, 220 employees",
        recent_news_or_signals=["Raised Series B"],
        notable_tech_or_tools_mentioned=["Kubernetes", "AWS"],
        source_urls=["https://cloudscaledata.io"],
        raw_context_used=["[Web Content]: Observability platform."],
    )
    icp = ICPClassification(
        fit_score=0.90,
        fit_label="strong_fit",
        rationale="Ideal stage and vertical alignment.",
        matched_criteria=["Series B", "DevOps vertical"],
        mismatched_criteria=[],
    )
    return research, icp


@pytest.mark.asyncio
async def test_synthesis_agent_successful_run(sample_inputs):
    research, icp = sample_inputs
    llm_payload = {
        "company_name": "CloudScale Data Inc",
        "industry": "DevOps / Cloud",
        "executive_summary": "CloudScale Data is a high-growth Series B Kubernetes observability platform.",
        "key_products_or_services": ["Kubernetes Observability", "Multi-Cloud Telemetry"],
        "likely_pain_points": ["Managing high cardinality telemetry at scale", "SDR research fatigue"],
        "suggested_talk_tracks": ["Highlight automated context gathering for DevOps workflows"],
        "objection_handling_notes": ["Objection: 'We build in-house' -> Rebuttal: 'Focus core engineering on product'"],
        "source_urls": ["https://cloudscaledata.io"],
    }
    mock_llm = MockLLMProvider(response_text=f"```json\n{json.dumps(llm_payload)}\n```")

    agent = SynthesisAgent(
        llm_provider=mock_llm,
        hybrid_retriever=MockRetriever(),
    )

    brief = await agent.run(research_output=research, icp_classification=icp)

    assert isinstance(brief, AccountBrief)
    assert brief.company_name == "CloudScale Data Inc"
    assert brief.industry == "DevOps / Cloud"
    assert brief.icp_classification.fit_label == "strong_fit"
    assert "CloudScale Data is a high-growth" in brief.executive_summary
    assert len(brief.key_products_or_services) == 2
    assert len(brief.likely_pain_points) == 2
    assert len(brief.suggested_talk_tracks) == 1
    assert len(brief.objection_handling_notes) == 1
    assert brief.source_urls == ["https://cloudscaledata.io"]


@pytest.mark.asyncio
async def test_synthesis_agent_with_unknown_icp(sample_inputs):
    research, _ = sample_inputs
    llm_payload = {
        "company_name": "CloudScale Data Inc",
        "executive_summary": "Account brief generated with unknown ICP.",
        "key_products_or_services": ["Observability"],
        "likely_pain_points": ["Scaling"],
        "suggested_talk_tracks": ["Talk track 1"],
        "objection_handling_notes": ["Note 1"],
        "source_urls": ["https://cloudscaledata.io"],
    }
    mock_llm = MockLLMProvider(response_text=json.dumps(llm_payload))
    agent = SynthesisAgent(llm_provider=mock_llm)

    # Pass None for icp_classification
    brief = await agent.run(research_output=research, icp_classification=None)

    assert brief.icp_classification.fit_label == "unknown"
    assert brief.icp_classification.fit_score is None


@pytest.mark.asyncio
async def test_synthesis_agent_failure_raises_error(sample_inputs):
    research, icp = sample_inputs
    mock_llm = MockFailingLLMProvider()
    agent = SynthesisAgent(llm_provider=mock_llm)

    with pytest.raises(RuntimeError, match="SynthesisAgent failed to generate AccountBrief"):
        await agent.run(research_output=research, icp_classification=icp)
