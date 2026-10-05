"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class LLMResponse(str):
    """A str subclass that carries LLM call observability metadata.

    Subclassing str keeps every existing usage pattern fully backward-compatible:
    json.loads(response), regex.search(response), response[:n], etc. all work
    without any change at the call site.

    Extra attributes are injected after construction via object.__setattr__
    because str is immutable.
    """

    def __new__(
        cls,
        text: str,
        latency_seconds: float = 0.0,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
    ) -> "LLMResponse":
        instance = super().__new__(cls, text)
        object.__setattr__(instance, "latency_seconds", latency_seconds)
        object.__setattr__(instance, "prompt_tokens", prompt_tokens)
        object.__setattr__(instance, "completion_tokens", completion_tokens)
        object.__setattr__(instance, "total_tokens", total_tokens)
        return instance

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"LLMResponse({str.__repr__(self)}, "
            f"latency={self.latency_seconds:.3f}s, "
            f"tokens={self.total_tokens})"
        )


class LLMProvider(ABC):
    """Abstract interface for large language model providers."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate a text completion for the given prompt.

        Args:
            prompt: User prompt text.
            system: Optional system instruction prompt.
            **kwargs: Additional provider-specific parameters (e.g. temperature, max_tokens).

        Returns:
            The raw text response from the model (may be an LLMResponse subclass
            carrying latency and token-usage metadata).
        """
        pass
