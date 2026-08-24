"""Unit tests for JSON extraction utilities."""

import pytest
from gtm_copilot.llm.json_utils import extract_json


def test_extract_json_pure():
    text = '{"company_name": "Acme Corp", "industry": "SaaS"}'
    data = extract_json(text)
    assert data["company_name"] == "Acme Corp"
    assert data["industry"] == "SaaS"


def test_extract_json_markdown_fence():
    text = """Here is the extracted information:
```json
{
  "company_name": "CloudScale Inc",
  "products_or_services": ["Analytics", "Observability"]
}
```
Hope this helps!"""
    data = extract_json(text)
    assert data["company_name"] == "CloudScale Inc"
    assert len(data["products_or_services"]) == 2


def test_extract_json_generic_fence():
    text = """```
{
  "company_name": "DataFlow",
  "industry": "Data Infrastructure"
}
```"""
    data = extract_json(text)
    assert data["company_name"] == "DataFlow"


def test_extract_json_trailing_comma():
    text = """{
  "company_name": "Acme",
  "products": ["P1", "P2",],
}"""
    data = extract_json(text)
    assert data["company_name"] == "Acme"


def test_extract_json_invalid_empty():
    with pytest.raises(ValueError, match="Cannot extract JSON from empty text"):
        extract_json("")
    with pytest.raises(ValueError, match="Cannot extract JSON from empty text"):
        extract_json("   ")


def test_extract_json_unparseable():
    with pytest.raises(ValueError, match="Failed to extract valid JSON"):
        extract_json("Sorry, I could not find any information about that company.")
