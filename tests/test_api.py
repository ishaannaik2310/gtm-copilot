"""Unit tests for FastAPI REST API endpoints."""

from typing import List, Optional
import pytest
from fastapi.testclient import TestClient

from gtm_copilot.agents.base import BaseAgent
from gtm_copilot.api.main import create_app
from gtm_copilot.models import (
    AccountBrief,
    FactCheckedBrief,
    FactCheckResult,
    ICPClassification,
    ResearchInput,
)
from gtm_copilot.orchestrator import AccountBriefOrchestrator


class MockOrchestrator(AccountBriefOrchestrator):
    """Mock orchestrator returning predefined FactCheckedBrief."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.last_input: Optional[ResearchInput] = None

    async def run(self, input: ResearchInput) -> FactCheckedBrief:
        self.last_input = input
        if self.should_fail:
            raise RuntimeError("Orchestrator synthesis failed.")

        brief = AccountBrief(
            company_name=input.company_name or "MockCompany",
            industry="Enterprise Software",
            icp_classification=ICPClassification(
                fit_score=0.9,
                fit_label="strong_fit",
                rationale="Good alignment.",
                matched_criteria=["Enterprise"],
                mismatched_criteria=[],
            ),
            executive_summary="Mock executive summary.",
            key_products_or_services=["Product A", "Product B"],
            likely_pain_points=["Scaling sales operations"],
            suggested_talk_tracks=["Talk track 1"],
            objection_handling_notes=["Objection 1"],
            source_urls=[input.url] if input.url else [],
        )

        return FactCheckedBrief(
            brief=brief,
            fact_checks=[
                FactCheckResult(
                    claim="Mock executive summary.",
                    status="directly_supported",
                    supported=True,
                    supporting_evidence="Supported by mock data.",
                    confidence=1.0,
                )
            ],
            overall_faithfulness_score=1.0,
            flagged_claims=[],
        )


@pytest.fixture
def client():
    app = create_app()
    # Inject mock orchestrator into app.state to isolate from live LLM/network
    app.state.orchestrator = MockOrchestrator(should_fail=False)
    return TestClient(app)


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_brief_success(client):
    payload = {
        "company_name": "Notion",
        "url": "https://www.notion.so",
    }
    response = client.post("/api/brief", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "brief" in data
    assert data["brief"]["company_name"] == "Notion"
    assert data["brief"]["icp_classification"]["fit_label"] == "strong_fit"
    assert data["overall_faithfulness_score"] == 1.0
    assert len(data["fact_checks"]) == 1
    assert data["fact_checks"][0]["status"] == "directly_supported"


def test_generate_brief_invalid_input_empty_body(client):
    # Both fields missing
    response = client.post("/api/brief", json={})
    assert response.status_code == 400
    assert "At least one of 'company_name' or 'url'" in response.json()["detail"]


def test_generate_brief_invalid_input_whitespace(client):
    # Both fields blank whitespace
    response = client.post("/api/brief", json={"company_name": "   ", "url": "  "})
    assert response.status_code == 400
    assert "At least one of 'company_name' or 'url'" in response.json()["detail"]


def test_generate_brief_orchestrator_failure():
    app = create_app()
    app.state.orchestrator = MockOrchestrator(should_fail=True)
    failing_client = TestClient(app)

    response = failing_client.post("/api/brief", json={"company_name": "Notion"})
    assert response.status_code == 500
    assert "Account brief generation failed" in response.json()["detail"]
    assert "Orchestrator synthesis failed" in response.json()["detail"]
