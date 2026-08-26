"""Unit tests for FastAPI REST API endpoints."""

from typing import List, Optional
import pytest
from fastapi.testclient import TestClient

from gtm_copilot.agents.base import BaseAgent
from gtm_copilot.api.main import create_app
from gtm_copilot.models import (
    AccountBrief,
    EmailVariant,
    FactCheckedBrief,
    FactCheckedOutreach,
    FactCheckResult,
    FollowUpVariant,
    ICPClassification,
    OutreachInput,
    OutreachOutput,
    ResearchInput,
)
from gtm_copilot.orchestrator import AccountBriefOrchestrator


class MockOrchestrator(AccountBriefOrchestrator):
    """Mock orchestrator returning predefined FactCheckedBrief and FactCheckedOutreach."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.last_input: Optional[ResearchInput] = None
        self.last_outreach_input: Optional[OutreachInput] = None

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

    async def generate_outreach(self, input: OutreachInput) -> FactCheckedOutreach:
        self.last_outreach_input = input
        if self.should_fail:
            raise RuntimeError("Outreach orchestrator generation failed.")

        outreach = OutreachOutput(
            contact_name=input.contact_name,
            email_variants=[
                EmailVariant(
                    subject="Scale enterprise deal velocity for MockCompany",
                    body="Hi, noticed MockCompany scaling. We automate research into 2-minute dossiers.",
                    tone_label="direct",
                )
            ],
            follow_up_sequence=[
                FollowUpVariant(
                    subject="Re: Scale enterprise deal velocity",
                    body="Following up on our pre-call research platform note.",
                    send_after_days=3,
                    sequence_position=1,
                )
            ],
            personalization_notes=["MockCompany growth signals."],
            source_grounding=["Grounding context."],
        )

        return FactCheckedOutreach(
            outreach=outreach,
            fact_checks=[
                FactCheckResult(
                    claim="We automate research into 2-minute dossiers.",
                    status="directly_supported",
                    supported=True,
                    supporting_evidence="Playbook value props.",
                    confidence=0.95,
                )
            ],
            overall_faithfulness_score=1.0,
            flagged_claims=[],
        )


@pytest.fixture
def client():
    app = create_app()
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
    response = client.post("/api/brief", json={})
    assert response.status_code == 400
    assert "At least one of 'company_name' or 'url'" in response.json()["detail"]


def test_generate_brief_invalid_input_whitespace(client):
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


def test_generate_outreach_success(client):
    sample_brief = {
        "company_name": "Notion Labs",
        "industry": "Enterprise Software",
        "icp_classification": {
            "fit_score": 0.9,
            "fit_label": "strong_fit",
            "rationale": "Good fit",
            "matched_criteria": ["Enterprise"],
            "mismatched_criteria": [],
        },
        "executive_summary": "Notion is an AI workspace.",
        "key_products_or_services": ["Notion AI", "Docs"],
        "likely_pain_points": ["Sales research time"],
        "suggested_talk_tracks": ["Accelerate pre-call prep"],
        "objection_handling_notes": ["Security objection"],
        "source_urls": ["https://www.notion.so"],
    }

    payload = {
        "account_brief": sample_brief,
        "contact_name": "Sarah Connor",
        "contact_role": "VP Sales",
        "contact_linkedin_or_notes": "Scaling enterprise AEs.",
    }

    response = client.post("/api/outreach", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "outreach" in data
    assert data["outreach"]["contact_name"] == "Sarah Connor"
    assert len(data["outreach"]["email_variants"]) == 1
    assert data["overall_faithfulness_score"] == 1.0


def test_generate_outreach_invalid_empty_company_name(client):
    payload = {
        "account_brief": {
            "company_name": "   ",
            "industry": "Software",
            "icp_classification": {
                "fit_score": 0.5,
                "fit_label": "possible_fit",
                "rationale": "R",
                "matched_criteria": [],
                "mismatched_criteria": [],
            },
            "executive_summary": "Summary",
            "key_products_or_services": [],
            "likely_pain_points": [],
            "suggested_talk_tracks": [],
            "objection_handling_notes": [],
            "source_urls": [],
        }
    }

    response = client.post("/api/outreach", json=payload)
    assert response.status_code == 400
    assert "Invalid AccountBrief" in response.json()["detail"]


def test_generate_outreach_orchestrator_failure():
    app = create_app()
    app.state.orchestrator = MockOrchestrator(should_fail=True)
    failing_client = TestClient(app)

    sample_brief = {
        "company_name": "Notion Labs",
        "industry": "Enterprise Software",
        "icp_classification": {
            "fit_score": 0.9,
            "fit_label": "strong_fit",
            "rationale": "Good fit",
            "matched_criteria": [],
            "mismatched_criteria": [],
        },
        "executive_summary": "Notion is an AI workspace.",
        "key_products_or_services": [],
        "likely_pain_points": [],
        "suggested_talk_tracks": [],
        "objection_handling_notes": [],
        "source_urls": [],
    }

    response = failing_client.post("/api/outreach", json={"account_brief": sample_brief})
    assert response.status_code == 500
    assert "Outreach generation failed" in response.json()["detail"]
