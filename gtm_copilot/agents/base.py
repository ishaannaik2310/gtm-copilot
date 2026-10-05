"""Abstract Base Agent definition."""

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from gtm_copilot.llm.base import LLMResponse
from gtm_copilot.models import AgentCallMetrics


class BaseAgent(ABC):
    """Abstract base class for all specialized AI agents."""

    def __init__(self, name: str):
        """Initialize base agent with an identifying name.

        Args:
            name: Identifier for the agent.
        """
        self.name = name
        self._call_metrics: List[AgentCallMetrics] = []

    async def call_llm(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Call the LLM provider, record observability metrics, and return the text response.

        This is the preferred way for all agents to invoke the LLM — it is a thin wrapper
        around ``self.llm_provider.complete()`` that:

        1. Records wall-clock latency via ``LLMResponse.latency_seconds`` (populated by
           ``GeminiProvider``).
        2. Captures token counts (``prompt_tokens``, ``completion_tokens``, ``total_tokens``).
        3. Calculates estimated USD cost via the pricing table.
        4. Appends an ``AgentCallMetrics`` entry to ``self._call_metrics``.

        The return value is a plain ``str`` — callers can use ``json.loads()``, regex, slicing,
        or any other string operation without modification.

        This method does NOT change any prompt text, system instructions, or output content —
        it is purely additive instrumentation.

        Args:
            prompt: User prompt text to send to the LLM.
            system: Optional system instruction string.
            model: Optional model name override (used for cost lookup only; the actual
                   model used is determined by the provider's configuration).
            **kwargs: Additional kwargs forwarded to ``llm_provider.complete()``.

        Returns:
            Raw text response from the model as a plain ``str``.
        """
        from gtm_copilot.llm.pricing import calculate_gemini_cost  # local import avoids circular dep

        response = await self.llm_provider.complete(prompt=prompt, system=system, **kwargs)

        # Extract observability metadata if provider returned an LLMResponse
        latency = getattr(response, "latency_seconds", 0.0)
        prompt_tokens: Optional[int] = getattr(response, "prompt_tokens", None)
        completion_tokens: Optional[int] = getattr(response, "completion_tokens", None)
        total_tokens: Optional[int] = getattr(response, "total_tokens", None)

        # Use configured model name for pricing if not overridden
        resolved_model: Optional[str] = model or getattr(
            getattr(self, "llm_provider", None), "model", None
        )
        estimated_cost = calculate_gemini_cost(
            resolved_model or "",
            prompt_tokens,
            completion_tokens,
        ) if resolved_model else None

        self._call_metrics.append(
            AgentCallMetrics(
                agent_name=self.name,
                latency_seconds=latency,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=estimated_cost,
                model=resolved_model,
            )
        )

        return str(response)

    def flush_metrics(self) -> List[AgentCallMetrics]:
        """Return and clear accumulated call metrics for this agent.

        Called by the orchestrator after each pipeline stage to collect
        metrics before resetting for the next run.

        Returns:
            List of AgentCallMetrics recorded since last flush.
        """
        metrics = list(self._call_metrics)
        self._call_metrics.clear()
        return metrics

    @abstractmethod
    async def run(self, input: Any) -> Any:
        """Execute the agent workflow for the given input.

        Args:
            input: Domain-specific input payload.

        Returns:
            Domain-specific output payload.
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"
