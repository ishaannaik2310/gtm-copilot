"""LLM provider abstraction module."""

import os
from typing import Optional

from gtm_copilot.config import (
    ANTHROPIC_API_KEY,
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_OPENAI_MODEL,
    OPENAI_API_KEY,
)
from gtm_copilot.llm.anthropic_provider import AnthropicProvider
from gtm_copilot.llm.base import LLMProvider
from gtm_copilot.llm.json_utils import extract_json
from gtm_copilot.llm.openai_provider import OpenAIProvider


def get_llm_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> LLMProvider:
    """Factory helper to obtain configured LLM provider instance.

    Args:
        provider_name: 'openai' or 'anthropic'. Defaults to config.DEFAULT_LLM_PROVIDER.
        api_key: Optional explicit API key.
        model: Optional model name override.
        **kwargs: Additional provider arguments.

    Returns:
        Configured LLMProvider instance.
    """
    chosen_provider = (provider_name or DEFAULT_LLM_PROVIDER or "openai").lower().strip()

    if chosen_provider == "anthropic":
        return AnthropicProvider(
            api_key=api_key or ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", ""),
            model=model or DEFAULT_ANTHROPIC_MODEL,
            **kwargs,
        )

    return OpenAIProvider(
        api_key=api_key or OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", ""),
        model=model or DEFAULT_OPENAI_MODEL,
        **kwargs,
    )


__all__ = [
    "AnthropicProvider",
    "LLMProvider",
    "OpenAIProvider",
    "extract_json",
    "get_llm_provider",
]
