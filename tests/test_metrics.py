"""Tests for pipeline performance observability: LLMResponse, pricing, BaseAgent.call_llm, and orchestrator metrics."""

import asyncio
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gtm_copilot.llm.base import LLMResponse
from gtm_copilot.llm.pricing import calculate_gemini_cost
from gtm_copilot.models import AgentCallMetrics, PipelineMetrics


# ---------------------------------------------------------------------------
# LLMResponse — str subclass behaviour
# ---------------------------------------------------------------------------


class TestLLMResponse:
    def test_is_str_subclass(self):
        resp = LLMResponse("hello world")
        assert isinstance(resp, str)
        assert resp == "hello world"

    def test_str_operations_work(self):
        resp = LLMResponse('{"key": "value"}')
        import json

        parsed = json.loads(resp)
        assert parsed == {"key": "value"}

    def test_slicing_works(self):
        resp = LLMResponse("abcdef", latency_seconds=0.5)
        assert resp[:3] == "abc"

    def test_carries_metadata(self):
        resp = LLMResponse(
            "text",
            latency_seconds=1.23,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        assert resp.latency_seconds == 1.23
        assert resp.prompt_tokens == 100
        assert resp.completion_tokens == 50
        assert resp.total_tokens == 150

    def test_defaults_are_none_or_zero(self):
        resp = LLMResponse("bare text")
        assert resp.latency_seconds == 0.0
        assert resp.prompt_tokens is None
        assert resp.completion_tokens is None
        assert resp.total_tokens is None

    def test_regex_works(self):
        import re

        resp = LLMResponse("Temperature: 37.5°C")
        match = re.search(r"(\d+\.\d+)", resp)
        assert match is not None
        assert match.group(1) == "37.5"

    def test_concat_returns_plain_str(self):
        resp = LLMResponse("hello")
        # Concatenation with str returns plain str (Python's str behaviour)
        result = resp + " world"
        assert result == "hello world"

    def test_empty_string(self):
        resp = LLMResponse("", latency_seconds=0.0)
        assert resp == ""
        assert len(resp) == 0


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


class TestCalculateGeminiCost:
    def test_known_model_returns_float(self):
        cost = calculate_gemini_cost("gemini-flash-lite-latest", 1_000_000, 1_000_000)
        assert isinstance(cost, float)
        assert cost > 0

    def test_cost_formula_correct(self):
        # gemini-flash-lite-latest: $0.075/1M prompt, $0.30/1M completion
        cost = calculate_gemini_cost("gemini-flash-lite-latest", 1_000_000, 1_000_000)
        expected = 0.075 + 0.30
        assert abs(cost - expected) < 1e-6

    def test_zero_tokens_gives_zero_cost(self):
        cost = calculate_gemini_cost("gemini-flash-lite-latest", 0, 0)
        assert cost == 0.0

    def test_returns_none_for_unknown_model(self):
        cost = calculate_gemini_cost("gpt-5-turbo-mega", 1000, 500)
        assert cost is None

    def test_returns_none_when_tokens_none(self):
        cost = calculate_gemini_cost("gemini-flash-lite-latest", None, None)
        assert cost is None

    def test_returns_none_when_prompt_tokens_none(self):
        cost = calculate_gemini_cost("gemini-flash-lite-latest", None, 500)
        assert cost is None

    def test_prefix_matching(self):
        # "gemini-2.0-flash-exp" should match "gemini-2.0-flash" pricing
        cost = calculate_gemini_cost("gemini-2.0-flash-experimental", 1_000_000, 1_000_000)
        assert cost is not None
        assert cost > 0

    def test_all_models_in_table_calculate(self):
        from gtm_copilot.llm.pricing import _PRICING

        for model in _PRICING:
            cost = calculate_gemini_cost(model, 1000, 500)
            assert cost is not None
            assert cost >= 0

    def test_cost_is_rounded_to_8_decimal_places(self):
        cost = calculate_gemini_cost("gemini-flash-lite-latest", 123_456, 78_901)
        assert cost is not None
        # result should be a float with at most 8 significant decimal places
        assert cost == round(cost, 8)


# ---------------------------------------------------------------------------
# BaseAgent.call_llm — metrics recording
# ---------------------------------------------------------------------------


class ConcreteAgent:
    """Minimal concrete agent for testing call_llm without importing abstract class issues."""

    def __init__(self, llm_provider):
        from gtm_copilot.agents.base import BaseAgent

        # Dynamically attach BaseAgent methods to this instance
        # (avoids needing to create a full concrete subclass with run())
        self.name = "test_agent"
        self._call_metrics = []
        self.llm_provider = llm_provider
        self.call_llm = BaseAgent.call_llm.__get__(self, type(self))
        self.flush_metrics = BaseAgent.flush_metrics.__get__(self, type(self))


class TestBaseAgentCallLLM:
    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock()
        provider.model = "gemini-flash-lite-latest"
        return provider

    @pytest.mark.asyncio
    async def test_call_llm_records_metrics(self, mock_provider):
        llm_response = LLMResponse(
            "result text",
            latency_seconds=0.88,
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
        )
        mock_provider.complete = AsyncMock(return_value=llm_response)

        agent = ConcreteAgent(mock_provider)
        result = await agent.call_llm(prompt="test prompt", system="sys")

        assert result == "result text"
        assert len(agent._call_metrics) == 1

        m = agent._call_metrics[0]
        assert m.agent_name == "test_agent"
        assert m.latency_seconds == 0.88
        assert m.prompt_tokens == 200
        assert m.completion_tokens == 100
        assert m.total_tokens == 300
        assert m.model == "gemini-flash-lite-latest"
        assert m.estimated_cost_usd is not None
        assert m.estimated_cost_usd > 0

    @pytest.mark.asyncio
    async def test_call_llm_with_plain_str_response(self, mock_provider):
        """When provider returns plain str (no LLMResponse), metrics still record with defaults."""
        mock_provider.complete = AsyncMock(return_value="plain string response")

        agent = ConcreteAgent(mock_provider)
        result = await agent.call_llm(prompt="test")

        assert result == "plain string response"
        assert len(agent._call_metrics) == 1

        m = agent._call_metrics[0]
        assert m.latency_seconds == 0.0
        assert m.prompt_tokens is None
        assert m.completion_tokens is None

    @pytest.mark.asyncio
    async def test_flush_metrics_clears_list(self, mock_provider):
        llm_response = LLMResponse("text", latency_seconds=0.5)
        mock_provider.complete = AsyncMock(return_value=llm_response)

        agent = ConcreteAgent(mock_provider)
        await agent.call_llm(prompt="a")
        await agent.call_llm(prompt="b")

        metrics = agent.flush_metrics()
        assert len(metrics) == 2
        assert len(agent._call_metrics) == 0  # cleared

    @pytest.mark.asyncio
    async def test_flush_metrics_returns_empty_when_no_calls(self, mock_provider):
        agent = ConcreteAgent(mock_provider)
        metrics = agent.flush_metrics()
        assert metrics == []


# ---------------------------------------------------------------------------
# Orchestrator metrics aggregation
# ---------------------------------------------------------------------------


class TestAggregateMetrics:
    def _make_call(
        self,
        agent_name: str,
        latency: float,
        prompt_tokens: Optional[int],
        completion_tokens: Optional[int],
        total_tokens: Optional[int],
        cost: Optional[float],
    ) -> AgentCallMetrics:
        return AgentCallMetrics(
            agent_name=agent_name,
            latency_seconds=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
            model="gemini-flash-lite-latest",
        )

    def test_aggregate_empty_list(self):
        from gtm_copilot.orchestrator import AccountBriefOrchestrator

        result = AccountBriefOrchestrator._aggregate_metrics([])
        assert result.call_count == 0
        assert result.total_latency_seconds == 0.0
        assert result.total_tokens == 0
        assert result.total_estimated_cost_usd is None  # empty = no costs → None

    def test_aggregate_sums_correctly(self):
        from gtm_copilot.orchestrator import AccountBriefOrchestrator

        calls = [
            self._make_call("research", 1.0, 100, 50, 150, 0.0001),
            self._make_call("synthesis", 2.0, 200, 100, 300, 0.0002),
            self._make_call("fact_check", 0.5, 50, 25, 75, 0.00005),
        ]
        result = AccountBriefOrchestrator._aggregate_metrics(calls)

        assert result.call_count == 3
        assert abs(result.total_latency_seconds - 3.5) < 0.001
        assert result.total_prompt_tokens == 350
        assert result.total_completion_tokens == 175
        assert result.total_tokens == 525
        assert result.total_estimated_cost_usd is not None
        assert abs(result.total_estimated_cost_usd - 0.00035) < 1e-8

    def test_aggregate_cost_none_when_any_call_has_no_cost(self):
        from gtm_copilot.orchestrator import AccountBriefOrchestrator

        calls = [
            self._make_call("research", 1.0, 100, 50, 150, 0.0001),
            self._make_call("icp", 0.8, None, None, None, None),  # no pricing
        ]
        result = AccountBriefOrchestrator._aggregate_metrics(calls)
        assert result.total_estimated_cost_usd is None

    def test_aggregate_preserves_agent_calls(self):
        from gtm_copilot.orchestrator import AccountBriefOrchestrator

        calls = [
            self._make_call("research", 1.0, 100, 50, 150, 0.0001),
            self._make_call("synthesis", 2.0, 200, 100, 300, 0.0002),
        ]
        result = AccountBriefOrchestrator._aggregate_metrics(calls)
        assert len(result.agent_calls) == 2
        assert result.agent_calls[0].agent_name == "research"
        assert result.agent_calls[1].agent_name == "synthesis"
