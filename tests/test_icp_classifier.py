"""Unit tests for ICPClassifierAgent."""

import json
from typing import Any, Optional
import pytest

from gtm_copilot.agents.icp_classifier import ICPClassifierAgent
from gtm_copilot.llm.base import LLMProvider
from gtm_copilot.models import Chunk, ICPClassification, ResearchOutput


class MockLLMProvider(LLMProvider):
    """Mock LLMProvider returning predefined text."""

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.last_prompt: Optional[str] = None
        self.last_system: Optional[str] = None

    async def complete(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> str:
        self.last_prompt = prompt
        self.last_system = system
        return self.response_text


class MockFailingLLMProvider(LLMProvider):
    """Mock LLMProvider that raises an exception."""

    async def complete(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> str:
        raise RuntimeError("Service unavailable")


class MockRetriever:
    """Mock retriever returning canned playbook chunks."""

    def retrieve(self, query: str, top_k: int = 5, filter_source_type: Optional[str] = None):
        return [
            Chunk(
                id="c-icp",
                document_id="doc-1",
                text="ICP Criteria: Series B to D high growth B2B SaaS organizations with 100-1000 employees.",
                metadata={"source_type": "playbook"},
            )
        ]


@pytest.fixture
def sample_research_output():
    return ResearchOutput(
        company_name="CloudScale Data Inc",
        industry="DevOps & Cloud Observability",
        products_or_services=["Kubernetes Monitor", "Cloud Insights"],
        apparent_company_size_signals="Series B stage, 220 employees",
        recent_news_or_signals=["Raised $42M"],
        notable_tech_or_tools_mentioned=["Kubernetes", "AWS"],
        source_urls=["https://cloudscaledata.io"],
        raw_context_used=["[Web Content]: Kubernetes monitoring platform."],
    )


@pytest.mark.asyncio
async def test_icp_classifier_strong_fit(sample_research_output):
    llm_payload = {
        "fit_score": 0.92,
        "fit_label": "strong_fit",
        "rationale": "Matches Series B stage and 100-1000 employee range in B2B SaaS.",
        "matched_criteria": [
            "Company Stage: Series B",
            "Employee Count: 220 within 100-1000 range",
            "Vertical: B2B SaaS / DevOps",
        ],
        "mismatched_criteria": [],
    }
    llm_response = f"```json\n{json.dumps(llm_payload)}\n```"
    mock_llm = MockLLMProvider(response_text=llm_response)

    agent = ICPClassifierAgent(
        llm_provider=mock_llm,
        hybrid_retriever=MockRetriever(),
    )

    result = await agent.run(sample_research_output)

    assert isinstance(result, ICPClassification)
    assert result.fit_label == "strong_fit"
    assert result.fit_score == 0.92
    assert len(result.matched_criteria) == 3
    assert len(result.mismatched_criteria) == 0
    assert "Matches Series B stage" in result.rationale
    assert mock_llm.last_system is not None


@pytest.mark.asyncio
async def test_icp_classifier_poor_fit(sample_research_output):
    llm_payload = {
        "fit_score": 0.15,
        "fit_label": "poor_fit",
        "rationale": "Early stage seed company with 5 employees, below ICP threshold.",
        "matched_criteria": [],
        "mismatched_criteria": ["Company Size: 5 employees (requires 100+)"],
    }
    mock_llm = MockLLMProvider(response_text=json.dumps(llm_payload))

    agent = ICPClassifierAgent(llm_provider=mock_llm)
    result = await agent.run(sample_research_output)

    assert result.fit_label == "poor_fit"
    assert result.fit_score == 0.15
    assert len(result.mismatched_criteria) == 1


@pytest.mark.asyncio
async def test_icp_classifier_malformed_json_fallback(sample_research_output):
    mock_llm = MockLLMProvider(response_text="Not valid JSON at all")
    agent = ICPClassifierAgent(llm_provider=mock_llm)

    result = await agent.run(sample_research_output)

    # Must degrade gracefully with unknown fit_label and None fit_score
    assert result.fit_label == "unknown"
    assert result.fit_score is None
    assert "ICP classification failed" in result.rationale


@pytest.mark.asyncio
async def test_icp_classifier_llm_exception_fallback(sample_research_output):
    mock_llm = MockFailingLLMProvider()
    agent = ICPClassifierAgent(llm_provider=mock_llm)

    result = await agent.run(sample_research_output)

    assert result.fit_label == "unknown"
    assert result.fit_score is None
    assert "ICP classification failed" in result.rationale
