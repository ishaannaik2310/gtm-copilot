"""Unit tests for GeminiProvider."""

import json
import logging
import httpx
import pytest

from gtm_copilot.config import log_gemini_key_status, sanitize_api_key
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
    # Key should NOT be in the URL query string
    assert "key=" not in captured_request["url"]
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
async def test_gemini_provider_401_rejected_key():
    def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"error": {"code": 401, "message": "API key not valid. Please pass a valid API key.", "status": "UNAUTHENTICATED"}},
        )

    mock_transport = httpx.MockTransport(handle_request)
    mock_client = httpx.AsyncClient(transport=mock_transport)

    provider = GeminiProvider(api_key="invalid-key", client=mock_client)
    with pytest.raises(RuntimeError, match="Gemini rejected the API key. Check GEMINI_API_KEY on the server"):
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


@pytest.mark.asyncio
async def test_gemini_provider_strips_newlines_and_whitespace():
    captured_url = ""
    captured_headers = {}

    def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url, captured_headers
        captured_url = str(request.url)
        captured_headers = dict(request.headers)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]},
        )

    mock_transport = httpx.MockTransport(handle_request)
    mock_client = httpx.AsyncClient(transport=mock_transport)

    # Pass api_key and model with leading/trailing newlines and spaces
    provider = GeminiProvider(
        api_key="  test-key-with-newline\n\r  ",
        model="  gemini-flash-lite-latest\n  ",
        client=mock_client,
    )

    result = await provider.complete(prompt="test")
    assert result == "ok"
    assert "\n" not in captured_url
    assert "\r" not in captured_url
    assert "key=" not in captured_url
    assert captured_headers["x-goog-api-key"] == "test-key-with-newline"
    assert "/models/gemini-flash-lite-latest:generateContent" in captured_url


@pytest.mark.asyncio
async def test_gemini_provider_env_with_trailing_newlines(monkeypatch):
    captured_url = ""
    captured_headers = {}

    def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url, captured_headers
        captured_url = str(request.url)
        captured_headers = dict(request.headers)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]},
        )

    mock_transport = httpx.MockTransport(handle_request)
    mock_client = httpx.AsyncClient(transport=mock_transport)

    monkeypatch.setenv("GEMINI_API_KEY", "env-key-with-newline\n")
    provider = GeminiProvider(client=mock_client)

    result = await provider.complete(prompt="test")
    assert result == "ok"
    assert "\n" not in captured_url
    assert "key=" not in captured_url
    assert captured_headers["x-goog-api-key"] == "env-key-with-newline"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw_input,expected_key",
    [
        ('"AIzaSyQuoteDouble"', "AIzaSyQuoteDouble"),
        ("'AIzaSyQuoteSingle'", "AIzaSyQuoteSingle"),
        ("GEMINI_API_KEY=AIzaSyPrefixOnly", "AIzaSyPrefixOnly"),
        ('GEMINI_API_KEY="AIzaSyPrefixDoubleQuotes"', "AIzaSyPrefixDoubleQuotes"),
        ("GEMINI_API_KEY='AIzaSyPrefixSingleQuotes'", "AIzaSyPrefixSingleQuotes"),
        ('"GEMINI_API_KEY=AIzaSyOuterDoubleQuotes"', "AIzaSyOuterDoubleQuotes"),
        ("'GEMINI_API_KEY=AIzaSyOuterSingleQuotes'", "AIzaSyOuterSingleQuotes"),
        ("  GEMINI_API_KEY=AIzaSyWhitespace  \n", "AIzaSyWhitespace"),
        ("  '  GEMINI_API_KEY=AIzaSyNested  '  ", "AIzaSyNested"),
    ],
)
async def test_gemini_provider_strips_quotes_and_prefix(raw_input, expected_key):
    captured_headers = {}

    def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal captured_headers
        captured_headers = dict(request.headers)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]},
        )

    mock_transport = httpx.MockTransport(handle_request)
    mock_client = httpx.AsyncClient(transport=mock_transport)

    provider = GeminiProvider(api_key=raw_input, client=mock_client)
    result = await provider.complete(prompt="test")
    assert result == "ok"
    assert captured_headers["x-goog-api-key"] == expected_key


def test_sanitize_api_key_helper():
    assert sanitize_api_key(None) == ""
    assert sanitize_api_key("") == ""
    assert sanitize_api_key("   ") == ""
    assert sanitize_api_key("AIzaSyNormalKey") == "AIzaSyNormalKey"
    assert sanitize_api_key('"AIzaSyDoubleQuoted"') == "AIzaSyDoubleQuoted"
    assert sanitize_api_key("'AIzaSySingleQuoted'") == "AIzaSySingleQuoted"
    assert sanitize_api_key("GEMINI_API_KEY=AIzaSyWithPrefix") == "AIzaSyWithPrefix"
    assert sanitize_api_key('GEMINI_API_KEY="AIzaSyPrefixDouble"') == "AIzaSyPrefixDouble"
    assert sanitize_api_key("GEMINI_API_KEY='AIzaSyPrefixSingle'") == "AIzaSyPrefixSingle"
    assert sanitize_api_key('"GEMINI_API_KEY=AIzaSyOuterDouble"') == "AIzaSyOuterDouble"
    assert sanitize_api_key("'GEMINI_API_KEY=AIzaSyOuterSingle'") == "AIzaSyOuterSingle"
    assert sanitize_api_key("  \n GEMINI_API_KEY=AIzaSyTrimmed \r\n ") == "AIzaSyTrimmed"


def test_log_gemini_key_status(caplog):
    # Case 1: Empty key
    with caplog.at_level(logging.WARNING):
        caplog.clear()
        log_gemini_key_status("")
        assert any("NOT SET" in rec.message for rec in caplog.records)
        assert any("starts_with_AIza=False" in rec.message for rec in caplog.records)

    # Case 2: Key does not start with AIza
    with caplog.at_level(logging.WARNING):
        caplog.clear()
        fake_key = "some_random_key_12345"
        log_gemini_key_status(fake_key)
        assert any("UNEXPECTED FORMAT" in rec.message for rec in caplog.records)
        assert any(f"length={len(fake_key)}" in rec.message for rec in caplog.records)
        assert any("starts_with_AIza=False" in rec.message for rec in caplog.records)
        # Verify the key itself is NEVER in the log records
        for rec in caplog.records:
            assert fake_key not in rec.message

    # Case 3: Valid AIza key
    with caplog.at_level(logging.INFO):
        caplog.clear()
        valid_key = "AIzaSyD_ExampleSecretKey12345"
        log_gemini_key_status(valid_key)
        assert any("SET (length=" in rec.message for rec in caplog.records)
        assert any("starts_with_AIza=True" in rec.message for rec in caplog.records)
        # Verify the key itself is NEVER in the log records
        for rec in caplog.records:
            assert valid_key not in rec.message


