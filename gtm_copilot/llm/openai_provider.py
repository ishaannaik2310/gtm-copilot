"""OpenAI LLM provider using direct async HTTP calls via httpx."""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from gtm_copilot.config import DEFAULT_OPENAI_MODEL, OPENAI_API_KEY
from gtm_copilot.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """LLM provider implementation for OpenAI Chat Completions API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_OPENAI_MODEL,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
        client: Optional[httpx.AsyncClient] = None,
    ):
        """Initialize OpenAIProvider.

        Args:
            api_key: OpenAI API key. Defaults to OPENAI_API_KEY from env.
            model: Model identifier (e.g. 'gpt-4o-mini', 'gpt-4o').
            base_url: Base endpoint URL for OpenAI API.
            timeout: Request timeout in seconds.
            client: Optional httpx.AsyncClient instance for testing/dependency injection.
        """
        self.api_key = api_key or OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
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
        """Send chat completion request to OpenAI API."""
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is missing. Set OPENAI_API_KEY environment variable or pass api_key."
            )

        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
        }
        for k, v in kwargs.items():
            if k not in payload:
                payload[k] = v

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/chat/completions"

        if self._client is not None:
            response = await self._client.post(url, json=payload, headers=headers, timeout=self.timeout)
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            logger.error("OpenAI API error %d: %s", response.status_code, response.text)
            raise RuntimeError(f"OpenAI API request failed ({response.status_code}): {response.text}")

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Unexpected response format from OpenAI API: {data}") from e
