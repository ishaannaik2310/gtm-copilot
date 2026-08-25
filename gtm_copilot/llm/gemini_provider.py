"""Gemini LLM provider using direct async HTTP calls via httpx."""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from gtm_copilot.config import DEFAULT_GEMINI_MODEL, GEMINI_API_KEY
from gtm_copilot.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """LLM provider implementation for Google Gemini API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_GEMINI_MODEL,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 60.0,
        client: Optional[httpx.AsyncClient] = None,
    ):
        """Initialize GeminiProvider.

        Args:
            api_key: Google Gemini API key. Defaults to GEMINI_API_KEY from environment.
            model: Model identifier (e.g. 'gemini-2.0-flash').
            base_url: Base endpoint URL for Gemini API.
            timeout: Request timeout in seconds.
            client: Optional httpx.AsyncClient instance for testing/dependency injection.
        """
        self.api_key = api_key if api_key is not None else (os.getenv("GEMINI_API_KEY") or "")
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
        """Send generation request to Google Gemini API."""
        resolved_key = self.api_key if self.api_key else (os.getenv("GEMINI_API_KEY") or "")
        if not resolved_key:
            raise ValueError(
                "Gemini API key is missing. Set GEMINI_API_KEY environment variable or pass api_key."
            )
        self.api_key = resolved_key

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.1),
            },
        }

        if system:
            payload["system_instruction"] = {
                "parts": [{"text": system}]
            }

        # Merge additional generation parameters
        if "max_output_tokens" in kwargs:
            payload["generationConfig"]["maxOutputTokens"] = kwargs["max_output_tokens"]
        if "top_p" in kwargs:
            payload["generationConfig"]["topP"] = kwargs["top_p"]

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": resolved_key,
        }

        url = f"{self.base_url}/models/{self.model}:generateContent?key={resolved_key}"

        max_attempts = 4
        response = None

        for attempt in range(1, max_attempts + 1):
            if self._client is not None:
                response = await self._client.post(url, json=payload, headers=headers, timeout=self.timeout)
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                break

            if response.status_code in (429, 500, 502, 503) and attempt < max_attempts:
                # Extract retry delay from response or use progressive backoff
                retry_delay = 3.0 * attempt
                if response.status_code == 429:
                    try:
                        err_json = response.json()
                        for detail in err_json.get("error", {}).get("details", []):
                            if "retryDelay" in detail:
                                delay_str = str(detail["retryDelay"]).rstrip("s")
                                retry_delay = float(delay_str) + 1.0
                                break
                    except Exception:
                        pass
                logger.warning(
                    "Gemini API transient error (%d). Retrying in %.1fs (attempt %d/%d)...",
                    response.status_code,
                    retry_delay,
                    attempt,
                    max_attempts,
                )
                await asyncio.sleep(retry_delay)
                continue

            # Non-retryable error or exhausted attempts
            logger.error("Gemini API error %d: %s", response.status_code, response.text)
            raise RuntimeError(f"Gemini API request failed ({response.status_code}): {response.text}")

        data = response.json()
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError(f"No candidates returned by Gemini API: {data}")
            return candidates[0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Unexpected response format from Gemini API: {data}") from e
