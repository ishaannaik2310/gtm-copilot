"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, Optional


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
            The raw text response from the model.
        """
        pass
