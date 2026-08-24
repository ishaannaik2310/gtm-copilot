"""Anthropic LLM provider using direct async HTTP calls via httpx."""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from gtm_copilot.config import ANTHROPIC_API_KEY, DEFAULT_ANTHROPIC_MODEL
from gtm_copilot.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """LLM provider implementation for Anthropic Messages API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_ANTHROPIC_MODEL,
        base_url: str = "https://api.anthropic.com/v1",
        timeout: float = 30.0,
        client: Optional[httpx.AsyncClient] = None,
    ):
        """Initialize AnthropicProvider.

        Args:
            api_key: Anthropic API key. Defaults to ANTHROPIC_API_KEY from env.
            model: Model identifier (e.g. 'claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307').
            base_url: Base endpoint URL for Anthropic API.
            timeout: Request timeout in seconds.
            client: Optional httpx.AsyncClient instance for testing/dependency injection.
        """
        self.api_key = api_key or ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Send message request to Anthropic API."""
        if not self.api_key:
            raise ValueError(
                "Anthropic API key is missing. Set ANTHROPIC_API_KEY environment variable or pass api_key."
            )

        messages: List[Dict[str, str]] = [{"role": "user", "content": prompt}]

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.1),
        }
        if system:
            payload["system"] = system

        for k, v in kwargs.items():
            if k not in payload:
                payload[k] = v

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        url = f"{self.base_url}/messages"

        if self._client is not None:
            response = await self._client.post(url, json=payload, headers=headers, timeout=self.timeout)
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            logger.error("Anthropic API error %d: %s", response.status_code, response.text)
            raise RuntimeError(f"Anthropic API request failed ({response.status_code}): {response.text}")

        data = response.json()
        try:
            return data["content"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Unexpected response format from Anthropic API: {data}") from e
