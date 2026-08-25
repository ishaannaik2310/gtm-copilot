"""Unit tests for GeminiProvider."""

import json
import httpx
import pytest

from gtm_copilot.llm.gemini_provider import GeminiProvider


@pytest.mark.asyncio
async def test_gemini_provider_complete_success():
    captured_request = {}

    def handle_request(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["body"] = json.loads(request.content.decode("utf-8"))
        captured_request["headers"] = dict(request.headers)

        response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": '{"company_name": "CloudScale", "industry": "DevOps"}'}
                        ],
                        "role": "model",
                    },
                    "finishReason": "STOP",
                }
            ]
        }
        return httpx.Response(200, json=response_data)

    mock_transport = httpx.MockTransport(handle_request)
    mock_client = httpx.AsyncClient(transport=mock_transport)

    provider = GeminiProvider(
        api_key="test-gemini-key",
        model="gemini-2.0-flash",
        client=mock_client,
    )

    result = await provider.complete(
        prompt="Extract info for CloudScale",
        system="You are a research analyst.",
        temperature=0.2,
    )

    assert result == '{"company_name": "CloudScale", "industry": "DevOps"}'
    assert "key=test-gemini-key" in captured_request["url"]
    assert captured_request["headers"]["x-goog-api-key"] == "test-gemini-key"
    assert captured_request["body"]["system_instruction"]["parts"][0]["text"] == "You are a research analyst."
    assert captured_request["body"]["contents"][0]["parts"][0]["text"] == "Extract info for CloudScale"
    assert captured_request["body"]["generationConfig"]["temperature"] == 0.2


@pytest.mark.asyncio
async def test_gemini_provider_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    provider = GeminiProvider(api_key="")
    with pytest.raises(ValueError, match="Gemini API key is missing"):
        await provider.complete(prompt="hello")


@pytest.mark.asyncio
async def test_gemini_provider_api_error():
    def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "Invalid argument"}})

    mock_transport = httpx.MockTransport(handle_request)
    mock_client = httpx.AsyncClient(transport=mock_transport)

    provider = GeminiProvider(api_key="valid-key", client=mock_client)
    with pytest.raises(RuntimeError, match="Gemini API request failed"):
        await provider.complete(prompt="hello")


@pytest.mark.asyncio
async def test_gemini_provider_empty_candidates():
    def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": []})

    mock_transport = httpx.MockTransport(handle_request)
    mock_client = httpx.AsyncClient(transport=mock_transport)

    provider = GeminiProvider(api_key="valid-key", client=mock_client)
    with pytest.raises(ValueError, match="No candidates returned"):
        await provider.complete(prompt="hello")
