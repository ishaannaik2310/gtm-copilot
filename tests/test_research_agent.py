"""Unit tests for ResearchAgent."""

import json
from typing import Any, Optional
import httpx
import pytest

from gtm_copilot.agents.research_agent import (
    ResearchAgent,
    extract_visible_text_from_html,
)
from gtm_copilot.llm.base import LLMProvider
from gtm_copilot.models import Chunk, ResearchInput, ResearchOutput


class MockLLMProvider(LLMProvider):
    """Mock LLMProvider returning canned completions."""

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
        raise RuntimeError("LLM service unavailable")


class MockRetriever:
    """Mock hybrid retriever for internal knowledge base testing."""

    def retrieve(self, query: str, top_k: int = 5, filter_source_type: Optional[str] = None):
        return [
            Chunk(
                id="c-playbook",
                document_id="doc-1",
                text="ICP Playbook: Target B2B SaaS companies with 100-1000 employees.",
                metadata={"source_type": "playbook"},
            )
        ]


def test_research_input_validation():
    # Valid with name only
    inp1 = ResearchInput(company_name="CloudScale")
    assert inp1.company_name == "CloudScale"

    # Valid with url only
    inp2 = ResearchInput(url="https://cloudscaledata.io")
    assert inp2.url == "https://cloudscaledata.io"

    # Valid with both
    inp3 = ResearchInput(company_name="CloudScale", url="https://cloudscaledata.io")
    assert inp3.company_name == "CloudScale"
    assert inp3.url == "https://cloudscaledata.io"

    # Invalid with neither
    with pytest.raises(ValueError, match="At least one of 'company_name' or 'url' must be provided"):
        ResearchInput()

    with pytest.raises(ValueError, match="At least one of 'company_name' or 'url' must be provided"):
        ResearchInput(company_name="", url="   ")


def test_extract_visible_text_from_html():
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CloudScale - Real-Time Observability</title>
        <meta name="description" content="Automated cloud analytics for Kubernetes.">
        <script>console.log("ignore me");</script>
        <style>body { color: red; }</style>
    </head>
    <body>
        <nav><a href="/home">Home</a></nav>
        <h1>Welcome to CloudScale</h1>
        <p>We provide observability for multi-cloud Kubernetes clusters.</p>
        <footer>Copyright 2026</footer>
    </body>
    </html>
    """
    text = extract_visible_text_from_html(sample_html)
    assert "Title: CloudScale - Real-Time Observability" in text
    assert "Description: Automated cloud analytics" in text
    assert "Welcome to CloudScale" in text
    assert "console.log" not in text
    assert "color: red" not in text


@pytest.mark.asyncio
async def test_research_agent_successful_run():
    # Mock HTML response
    def handle_request(request: httpx.Request) -> httpx.Response:
        html_content = "<html><head><title>CloudScale Data</title></head><body><h1>CloudScale Platform</h1><p>Kubernetes monitoring for Series B startups.</p></body></html>"
        return httpx.Response(200, text=html_content)

    mock_transport = httpx.MockTransport(handle_request)
    mock_http_client = httpx.AsyncClient(transport=mock_transport)

    llm_payload = {
        "company_name": "CloudScale Data Inc",
        "industry": "Cloud Observability & DevOps",
        "products_or_services": ["Kubernetes Monitoring", "Multi-Cloud Analytics"],
        "apparent_company_size_signals": "Series B stage, ~200 employees",
        "recent_news_or_signals": ["Launched enterprise governance tier"],
        "notable_tech_or_tools_mentioned": ["Kubernetes", "Snowflake", "AWS", "Salesforce"],
    }
    llm_response = f"```json\n{json.dumps(llm_payload)}\n```"
    mock_llm = MockLLMProvider(response_text=llm_response)

    agent = ResearchAgent(
        llm_provider=mock_llm,
        hybrid_retriever=MockRetriever(),
        http_client=mock_http_client,
    )

    result = await agent.run(ResearchInput(company_name="CloudScale", url="https://cloudscaledata.io"))

    assert isinstance(result, ResearchOutput)
    assert result.company_name == "CloudScale Data Inc"
    assert result.industry == "Cloud Observability & DevOps"
    assert len(result.products_or_services) == 2
    assert "Kubernetes Monitoring" in result.products_or_services
    assert "Series B" in (result.apparent_company_size_signals or "")
    assert len(result.recent_news_or_signals) == 1
    assert "Kubernetes" in result.notable_tech_or_tools_mentioned
    assert "https://cloudscaledata.io" in result.source_urls
    assert len(result.raw_context_used) >= 1
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_research_agent_only_company_name():
    llm_payload = {
        "company_name": "Acme Corp",
        "industry": "Industrial SaaS",
        "products_or_services": ["Supply Chain Optimization"],
        "apparent_company_size_signals": None,
        "recent_news_or_signals": [],
        "notable_tech_or_tools_mentioned": [],
    }
    mock_llm = MockLLMProvider(response_text=json.dumps(llm_payload))

    agent = ResearchAgent(
        llm_provider=mock_llm,
        hybrid_retriever=MockRetriever(),
    )

    result = await agent.run(ResearchInput(company_name="Acme Corp"))

    assert result.company_name == "Acme Corp"
    assert result.industry == "Industrial SaaS"
    assert result.source_urls == []
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_research_agent_web_fetch_failure():
    # Return 404
    def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    mock_transport = httpx.MockTransport(handle_request)
    mock_http_client = httpx.AsyncClient(transport=mock_transport)

    llm_payload = {
        "company_name": "Unknown Co",
        "industry": "Technology",
        "products_or_services": [],
        "apparent_company_size_signals": None,
        "recent_news_or_signals": [],
        "notable_tech_or_tools_mentioned": [],
    }
    mock_llm = MockLLMProvider(response_text=json.dumps(llm_payload))

    agent = ResearchAgent(
        llm_provider=mock_llm,
        http_client=mock_http_client,
    )

    result = await agent.run(ResearchInput(url="https://broken-url-404.com"))

    assert len(result.errors) >= 1
    assert any("404" in err for err in result.errors)
    assert result.industry == "Technology"


@pytest.mark.asyncio
async def test_research_agent_malformed_llm_json():
    # LLM returns unparseable plain text
    mock_llm = MockLLMProvider(response_text="I am unable to generate valid JSON.")

    agent = ResearchAgent(llm_provider=mock_llm)

    result = await agent.run(ResearchInput(company_name="BrokenLLM Corp"))

    assert isinstance(result, ResearchOutput)
    assert result.company_name == "BrokenLLM Corp"
    assert len(result.errors) >= 1
    assert any("Failed to parse LLM JSON" in err for err in result.errors)


@pytest.mark.asyncio
async def test_research_agent_llm_exception():
    agent = ResearchAgent(llm_provider=MockFailingLLMProvider())

    result = await agent.run(ResearchInput(company_name="FailCorp"))

    assert isinstance(result, ResearchOutput)
    assert result.company_name == "FailCorp"
    assert len(result.errors) >= 1
    assert any("LLM completion error" in err for err in result.errors)
