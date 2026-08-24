"""LLM provider abstraction module."""

import os
from typing import Optional

from gtm_copilot.config import DEFAULT_GEMINI_MODEL, GEMINI_API_KEY
from gtm_copilot.llm.base import LLMProvider
from gtm_copilot.llm.gemini_provider import GeminiProvider
from gtm_copilot.llm.json_utils import extract_json


def get_default_llm_provider(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> LLMProvider:
    """Factory helper to obtain configured Gemini LLM provider instance.

    Args:
        api_key: Optional explicit API key. Defaults to GEMINI_API_KEY.
        model: Optional model name override. Defaults to DEFAULT_GEMINI_MODEL.
        **kwargs: Additional provider arguments.

    Returns:
        Configured GeminiProvider instance.
    """
    return GeminiProvider(
        api_key=api_key or GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", ""),
        model=model or DEFAULT_GEMINI_MODEL,
        **kwargs,
    )


def get_llm_provider(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> LLMProvider:
    """Alias for get_default_llm_provider."""
    return get_default_llm_provider(api_key=api_key, model=model, **kwargs)


__all__ = [
    "GeminiProvider",
    "LLMProvider",
    "extract_json",
    "get_default_llm_provider",
    "get_llm_provider",
]
